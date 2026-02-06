import { CommonModule } from '@angular/common';
import { AfterViewInit, Component, ElementRef, OnDestroy, OnInit, ViewChild } from '@angular/core';
import { interval, Subject, takeUntil } from 'rxjs';
import { MissionPlannerComponent } from '../mission-planner/mission-planner.component';
import { DroneService, TelemetryData } from '../services/drone.service';
import { GamepadInput, GamepadService } from '../services/gamepad.service';

interface Telemetry {
    lat: number | null;
    lon: number | null;
    alt: number | null;
    ground_speed: number | null;
    armed: boolean;
    mode: string;
    battery: number | null;
    heading?: number;
    pitch?: number;
    roll?: number;
}

interface ManualControls {
    pitch: number;
    roll: number;
    yaw: number;
    throttle: number;
}

@Component({
    selector: 'app-drone-fpv',
    standalone: true,
    imports: [CommonModule, MissionPlannerComponent],
    templateUrl: './drone-fpv.component.html',
    styleUrls: ['./drone-fpv.component.css']
})
export class DroneFpvComponent implements OnInit, OnDestroy, AfterViewInit {
    @ViewChild('videoCanvas', { static: false }) videoCanvas!: ElementRef<HTMLCanvasElement>;
    @ViewChild('hudCanvas', { static: false }) hudCanvas!: ElementRef<HTMLCanvasElement>;

    private destroy$ = new Subject<void>();
    private videoContext!: CanvasRenderingContext2D;
    private hudContext!: CanvasRenderingContext2D;
    private animationFrameId?: number;

    // State
    telemetry: Telemetry = {
        lat: null,
        lon: null,
        alt: 0,
        ground_speed: 0,
        armed: false,
        mode: 'UNKNOWN',
        battery: 100,
        heading: 0,
        pitch: 0,
        roll: 0
    };

    connectionStatus = 'disconnected';
    videoConnected = false;
    telemetryConnected = false;

    // Control modes
    controlMode: 'manual' | 'ai' = 'manual';
    showMapPlanner = false;
    manualControlEnabled = false;

    // Gamepad state
    gamepadConnected = false;
    gamepadName = '';
    manualControls: ManualControls = {
        pitch: 0,
        roll: 0,
        yaw: 0,
        throttle: 0.5
    };

    // Virtual joystick state (for touch/mouse)
    virtualJoystickActive = false;
    virtualJoystickPosition = { x: 0, y: 0 };

    constructor(
        private droneService: DroneService,
        private gamepadService: GamepadService
    ) { }

    ngOnInit() {
        this.connectDrone();
        this.setupGamepadMonitoring();
    }

    ngAfterViewInit() {
        this.initializeCanvases();
        this.startHudRendering();
    }

    ngOnDestroy() {
        this.destroy$.next();
        this.destroy$.complete();
        this.droneService.disconnect();
        this.gamepadService.stopPolling();
        if (this.animationFrameId) {
            cancelAnimationFrame(this.animationFrameId);
        }
    }

    // === Connection Management ===

    connectDrone() {
        // Connect video stream
        this.droneService.connectVideo().pipe(
            takeUntil(this.destroy$)
        ).subscribe({
            next: (frame: Blob) => {
                this.videoConnected = true;
                this.renderVideoFrame(frame);
            },
            error: (err: any) => {
                console.error('Video stream error:', err);
                this.videoConnected = false;
            }
        });

        // Connect telemetry stream
        this.droneService.connectTelemetry().pipe(
            takeUntil(this.destroy$)
        ).subscribe({
            next: (data: TelemetryData) => {
                this.telemetryConnected = true;
                // Map TelemetryData to component Telemetry format
                this.telemetry = {
                    lat: data.latitude,
                    lon: data.longitude,
                    alt: data.altitude,
                    ground_speed: data.speed,
                    armed: data.armed,
                    mode: data.mode,
                    battery: data.battery,
                    heading: data.heading,
                    pitch: data.pitch,
                    roll: data.roll
                };
            },
            error: (err: any) => {
                console.error('Telemetry stream error:', err);
                this.telemetryConnected = false;
            }
        });

        this.updateConnectionStatus();
    }

    updateConnectionStatus() {
        if (this.videoConnected && this.telemetryConnected) {
            this.connectionStatus = 'connected';
        } else if (this.videoConnected || this.telemetryConnected) {
            this.connectionStatus = 'partial';
        } else {
            this.connectionStatus = 'disconnected';
        }
    }

    // === Canvas Rendering ===

    initializeCanvases() {
        const videoCanvas = this.videoCanvas.nativeElement;
        const hudCanvas = this.hudCanvas.nativeElement;

        this.videoContext = videoCanvas.getContext('2d')!;
        this.hudContext = hudCanvas.getContext('2d')!;

        // Set canvas sizes
        videoCanvas.width = 1280;
        videoCanvas.height = 720;
        hudCanvas.width = 1280;
        hudCanvas.height = 720;
    }

    renderVideoFrame(blob: Blob) {
        createImageBitmap(blob).then(img => {
            this.videoContext.drawImage(img, 0, 0, 1280, 720);
        });
    }

    startHudRendering() {
        const render = () => {
            this.drawHUD();
            this.animationFrameId = requestAnimationFrame(render);
        };
        render();
    }

    drawHUD() {
        const ctx = this.hudContext;
        const width = 1280;
        const height = 720;

        // Clear canvas
        ctx.clearRect(0, 0, width, height);

        // Set zombie-green color scheme
        ctx.strokeStyle = '#00ff41';
        ctx.fillStyle = '#00ff41';
        ctx.font = '18px "Courier New", monospace';
        ctx.shadowColor = '#00ff41';
        ctx.shadowBlur = 5;

        // Draw center crosshair
        this.drawCrosshair(ctx, width / 2, height / 2);

        // Draw artificial horizon
        this.drawArtificialHorizon(ctx, width / 2, height / 2, this.telemetry.pitch || 0, this.telemetry.roll || 0);

        // Draw telemetry data (left side)
        this.drawTelemetryData(ctx);

        // Draw compass rose (top center)
        this.drawCompass(ctx, width / 2, 60, this.telemetry.heading || 0);

        // Draw altitude indicator (right side)
        this.drawAltitudeIndicator(ctx, width - 80, height / 2, this.telemetry.alt || 0);

        // Draw speed indicator (left side)
        this.drawSpeedIndicator(ctx, 80, height / 2, this.telemetry.ground_speed || 0);

        // Draw battery indicator (top right)
        this.drawBatteryIndicator(ctx, width - 150, 30, this.telemetry.battery || 0);

        // Draw armed status
        this.drawArmedStatus(ctx, width / 2, height - 50, this.telemetry.armed);

        // Reset shadow
        ctx.shadowBlur = 0;
    }

    drawCrosshair(ctx: CanvasRenderingContext2D, x: number, y: number) {
        ctx.lineWidth = 2;

        // Horizontal line
        ctx.beginPath();
        ctx.moveTo(x - 50, y);
        ctx.lineTo(x - 10, y);
        ctx.moveTo(x + 10, y);
        ctx.lineTo(x + 50, y);
        ctx.stroke();

        // Vertical line
        ctx.beginPath();
        ctx.moveTo(x, y - 50);
        ctx.lineTo(x, y - 10);
        ctx.moveTo(x, y + 10);
        ctx.lineTo(x, y + 50);
        ctx.stroke();

        // Center circle
        ctx.beginPath();
        ctx.arc(x, y, 30, 0, Math.PI * 2);
        ctx.stroke();

        // Center dot
        ctx.beginPath();
        ctx.arc(x, y, 3, 0, Math.PI * 2);
        ctx.fill();
    }

    drawArtificialHorizon(ctx: CanvasRenderingContext2D, x: number, y: number, pitch: number, roll: number) {
        ctx.save();
        ctx.translate(x, y);
        ctx.rotate(roll * Math.PI / 180);

        // Horizon line
        const horizonY = pitch * 2; // Scale pitch for visibility
        ctx.strokeStyle = '#00ff41';
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.moveTo(-200, horizonY);
        ctx.lineTo(200, horizonY);
        ctx.stroke();

        // Pitch ladder marks
        ctx.lineWidth = 2;
        for (let angle = -30; angle <= 30; angle += 10) {
            if (angle === 0) continue;
            const markY = horizonY + angle * 2;
            const markWidth = angle % 20 === 0 ? 40 : 20;

            ctx.beginPath();
            ctx.moveTo(-markWidth, markY);
            ctx.lineTo(markWidth, markY);
            ctx.stroke();

            // Label
            ctx.fillText(`${-angle}°`, markWidth + 10, markY + 5);
        }

        ctx.restore();
    }

    drawTelemetryData(ctx: CanvasRenderingContext2D) {
        const x = 20;
        let y = 30;
        const lineHeight = 25;

        ctx.fillStyle = '#00ff41';
        ctx.font = '16px "Courier New", monospace';

        const data = [
            `ALT: ${(this.telemetry.alt || 0).toFixed(1)}m`,
            `SPD: ${(this.telemetry.ground_speed || 0).toFixed(1)}m/s`,
            `HDG: ${(this.telemetry.heading || 0).toFixed(0)}°`,
            `BAT: ${(this.telemetry.battery || 0).toFixed(0)}%`,
            `MODE: ${this.telemetry.mode}`,
            `LAT: ${this.telemetry.lat?.toFixed(6) || 'N/A'}`,
            `LON: ${this.telemetry.lon?.toFixed(6) || 'N/A'}`
        ];

        data.forEach(line => {
            ctx.fillText(line, x, y);
            y += lineHeight;
        });
    }

    drawCompass(ctx: CanvasRenderingContext2D, x: number, y: number, heading: number) {
        ctx.save();
        ctx.translate(x, y);

        // Compass circle
        ctx.strokeStyle = '#00ff41';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(0, 0, 40, 0, Math.PI * 2);
        ctx.stroke();

        // North marker
        ctx.rotate(-heading * Math.PI / 180);
        ctx.fillStyle = '#ff0000';
        ctx.beginPath();
        ctx.moveTo(0, -35);
        ctx.lineTo(-5, -25);
        ctx.lineTo(5, -25);
        ctx.closePath();
        ctx.fill();

        // Heading text
        ctx.rotate(heading * Math.PI / 180);
        ctx.fillStyle = '#00ff41';
        ctx.font = 'bold 16px "Courier New", monospace';
        ctx.textAlign = 'center';
        ctx.fillText(`${heading.toFixed(0)}°`, 0, 60);

        ctx.restore();
    }

    drawAltitudeIndicator(ctx: CanvasRenderingContext2D, x: number, y: number, altitude: number) {
        const barHeight = 200;
        const barWidth = 30;

        // Background bar
        ctx.strokeStyle = '#00ff41';
        ctx.lineWidth = 2;
        ctx.strokeRect(x, y - barHeight / 2, barWidth, barHeight);

        // Altitude fill
        const fillHeight = Math.min(altitude / 100 * barHeight, barHeight);
        ctx.fillStyle = 'rgba(0, 255, 65, 0.3)';
        ctx.fillRect(x + 2, y + barHeight / 2 - fillHeight, barWidth - 4, fillHeight);

        // Current altitude text
        ctx.fillStyle = '#00ff41';
        ctx.font = 'bold 14px "Courier New", monospace';
        ctx.textAlign = 'center';
        ctx.fillText(`${altitude.toFixed(0)}m`, x + barWidth / 2, y + barHeight / 2 + 25);
    }

    drawSpeedIndicator(ctx: CanvasRenderingContext2D, x: number, y: number, speed: number) {
        const barHeight = 200;
        const barWidth = 30;

        // Background bar
        ctx.strokeStyle = '#00ff41';
        ctx.lineWidth = 2;
        ctx.strokeRect(x, y - barHeight / 2, barWidth, barHeight);

        // Speed fill
        const maxSpeed = 20; // m/s
        const fillHeight = Math.min(speed / maxSpeed * barHeight, barHeight);
        ctx.fillStyle = 'rgba(0, 255, 65, 0.3)';
        ctx.fillRect(x + 2, y + barHeight / 2 - fillHeight, barWidth - 4, fillHeight);

        // Current speed text
        ctx.fillStyle = '#00ff41';
        ctx.font = 'bold 14px "Courier New", monospace';
        ctx.textAlign = 'center';
        ctx.fillText(`${speed.toFixed(1)}m/s`, x + barWidth / 2, y + barHeight / 2 + 25);
    }

    drawBatteryIndicator(ctx: CanvasRenderingContext2D, x: number, y: number, battery: number) {
        const width = 60;
        const height = 25;

        // Battery outline
        ctx.strokeStyle = '#00ff41';
        ctx.lineWidth = 2;
        ctx.strokeRect(x, y, width, height);

        // Battery terminal
        ctx.fillRect(x + width, y + 7, 5, 11);

        // Battery fill
        const fillWidth = (battery / 100) * (width - 4);
        const fillColor = battery > 50 ? '#00ff41' : battery > 20 ? '#ffaa00' : '#ff0000';
        ctx.fillStyle = fillColor;
        ctx.fillRect(x + 2, y + 2, fillWidth, height - 4);

        // Battery percentage
        ctx.fillStyle = '#00ff41';
        ctx.font = 'bold 12px "Courier New", monospace';
        ctx.textAlign = 'center';
        ctx.fillText(`${battery.toFixed(0)}%`, x + width / 2, y + height + 15);
    }

    drawArmedStatus(ctx: CanvasRenderingContext2D, x: number, y: number, armed: boolean) {
        ctx.font = 'bold 18px "Courier New", monospace';
        ctx.textAlign = 'center';

        if (armed) {
            ctx.fillStyle = '#ff0000';
            ctx.shadowColor = '#ff0000';
            ctx.shadowBlur = 10;
            ctx.fillText('⚠ ARMED ⚠', x, y);
        } else {
            ctx.fillStyle = '#00ff41';
            ctx.shadowColor = '#00ff41';
            ctx.shadowBlur = 5;
            ctx.fillText('DISARMED', x, y);
        }
        ctx.shadowBlur = 0;
    }

    // === Control Mode Management ===

    toggleControlMode() {
        this.controlMode = this.controlMode === 'manual' ? 'ai' : 'manual';

        if (this.controlMode === 'ai') {
            this.manualControlEnabled = false;
            this.gamepadService.stopPolling();
        }
    }

    toggleMapPlanner() {
        this.showMapPlanner = !this.showMapPlanner;
    }

    // === Manual Control ===

    async enableManualControl() {
        if (this.controlMode !== 'manual') return;

        try {
            await this.droneService.requestManualControlToken();
            this.manualControlEnabled = true;

            if (this.gamepadConnected) {
                this.startGamepadControl();
            }
        } catch (err) {
            console.error('Failed to enable manual control:', err);
            alert('Failed to enable manual control. Check console for details.');
        }
    }

    disableManualControl() {
        this.manualControlEnabled = false;
        this.gamepadService.stopPolling();
        this.droneService.disableManualControl();
    }

    // === Gamepad Management ===

    setupGamepadMonitoring() {
        // Check for gamepad connection
        interval(1000).pipe(takeUntil(this.destroy$)).subscribe(() => {
            const gamepads = navigator.getGamepads();
            const gamepad = gamepads[0];

            if (gamepad && !this.gamepadConnected) {
                this.gamepadConnected = true;
                this.gamepadName = gamepad.id;
                console.log('Gamepad connected:', this.gamepadName);
            } else if (!gamepad && this.gamepadConnected) {
                this.gamepadConnected = false;
                this.gamepadName = '';
                console.log('Gamepad disconnected');
            }
        });
    }

    startGamepadControl() {
        // Start polling gamepad at 60Hz
        this.gamepadService.startPolling();

        // Subscribe to gamepad input observable
        this.gamepadService.gamepadInput$.subscribe((input: GamepadInput) => {
            if (!this.manualControlEnabled) return;

            // Map GamepadInput to ManualControls
            this.manualControls = {
                roll: input.leftStickX,
                pitch: input.leftStickY,
                yaw: input.rightStickX,
                throttle: input.rightStickY
            };
            this.droneService.sendManualControl(
                this.manualControls.roll,
                this.manualControls.pitch,
                this.manualControls.throttle,
                this.manualControls.yaw
            );
        });
    }

    // === Virtual Joystick (Touch/Mouse) ===

    onJoystickStart(event: MouseEvent | TouchEvent) {
        if (this.controlMode !== 'manual' || !this.manualControlEnabled) return;

        this.virtualJoystickActive = true;
        event.preventDefault();
    }

    onJoystickMove(event: MouseEvent | TouchEvent) {
        if (!this.virtualJoystickActive) return;

        const rect = (event.target as HTMLElement).getBoundingClientRect();
        let clientX: number, clientY: number;

        if (event instanceof MouseEvent) {
            clientX = event.clientX;
            clientY = event.clientY;
        } else {
            clientX = event.touches[0].clientX;
            clientY = event.touches[0].clientY;
        }

        const x = (clientX - rect.left - rect.width / 2) / (rect.width / 2);
        const y = (clientY - rect.top - rect.height / 2) / (rect.height / 2);

        this.virtualJoystickPosition = { x, y };

        // Map to control inputs
        this.manualControls = {
            pitch: -y,  // Inverted Y
            roll: x,
            yaw: 0,     // Would need second joystick
            throttle: 0.5
        };

        this.droneService.sendManualControl(
            this.manualControls.roll,
            this.manualControls.pitch,
            this.manualControls.throttle,
            this.manualControls.yaw
        );
    }

    onJoystickEnd() {
        this.virtualJoystickActive = false;
        this.virtualJoystickPosition = { x: 0, y: 0 };

        // Reset to neutral
        this.manualControls = {
            pitch: 0,
            roll: 0,
            yaw: 0,
            throttle: 0.5
        };

        this.droneService.sendManualControl(
            this.manualControls.roll,
            this.manualControls.pitch,
            this.manualControls.throttle,
            this.manualControls.yaw
        );
    }

    // === Quick Actions ===

    async arm() {
        try {
            await this.droneService.arm();
        } catch (err) {
            console.error('Arm failed:', err);
        }
    }

    async takeoff() {
        try {
            await this.droneService.takeoff();
        } catch (err) {
            console.error('Takeoff failed:', err);
        }
    }

    async land() {
        try {
            await this.droneService.land();
        } catch (err) {
            console.error('Land failed:', err);
        }
    }

    async rtl() {
        try {
            await this.droneService.returnToLaunch();
        } catch (err) {
            console.error('RTL failed:', err);
        }
    }
}
