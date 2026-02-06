import { Injectable, NgZone } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

export interface GamepadState {
    connected: boolean;
    id: string;
    buttons: boolean[];
    axes: number[];
}

export interface GamepadInput {
    leftStickX: number;   // Roll (left/right)
    leftStickY: number;   // Pitch (forward/back)
    rightStickX: number;  // Yaw (rotation)
    rightStickY: number;  // Throttle (up/down)
    buttonA: boolean;     // Typically used for confirm
    buttonB: boolean;     // Typically used for cancel
    buttonX: boolean;     // Custom action 1
    buttonY: boolean;     // Custom action 2
    leftBumper: boolean;  // L1
    rightBumper: boolean; // R1
    leftTrigger: number;  // L2 (0-1)
    rightTrigger: number; // R2 (0-1)
}

@Injectable({
    providedIn: 'root'
})
export class GamepadService {
    private gamepadIndex: number = -1;
    private gamepadStateSubject = new BehaviorSubject<GamepadState>({
        connected: false,
        id: '',
        buttons: [],
        axes: []
    });

    private gamepadInputSubject = new BehaviorSubject<GamepadInput>({
        leftStickX: 0,
        leftStickY: 0,
        rightStickX: 0,
        rightStickY: 0,
        buttonA: false,
        buttonB: false,
        buttonX: false,
        buttonY: false,
        leftBumper: false,
        rightBumper: false,
        leftTrigger: 0,
        rightTrigger: 0
    });

    public gamepadState$ = this.gamepadStateSubject.asObservable();
    public gamepadInput$ = this.gamepadInputSubject.asObservable();

    private pollingInterval: any = null;
    private readonly POLLING_RATE = 1000 / 60; // 60Hz
    private readonly DEADZONE = 0.15; // Ignore small stick movements

    constructor(private ngZone: NgZone) {
        console.log('[GamepadService] Initialized');
        this.setupGamepadListeners();
    }

    /**
     * Setup gamepad connection/disconnection listeners
     */
    private setupGamepadListeners(): void {
        window.addEventListener('gamepadconnected', (e: GamepadEvent) => {
            this.ngZone.run(() => {
                console.log('[GamepadService] Gamepad connected:', e.gamepad.id);
                this.gamepadIndex = e.gamepad.index;
                this.updateGamepadState(e.gamepad);
            });
        });

        window.addEventListener('gamepaddisconnected', (e: GamepadEvent) => {
            this.ngZone.run(() => {
                console.log('[GamepadService] Gamepad disconnected:', e.gamepad.id);
                if (this.gamepadIndex === e.gamepad.index) {
                    this.gamepadIndex = -1;
                    this.gamepadStateSubject.next({
                        connected: false,
                        id: '',
                        buttons: [],
                        axes: []
                    });
                }
            });
        });
    }

    /**
     * Start polling gamepad state
     */
    public startPolling(): void {
        if (this.pollingInterval) {
            console.warn('[GamepadService] Polling already active');
            return;
        }

        console.log('[GamepadService] Starting gamepad polling at 60Hz');

        this.pollingInterval = setInterval(() => {
            this.ngZone.run(() => {
                this.pollGamepad();
            });
        }, this.POLLING_RATE);
    }

    /**
     * Stop polling gamepad state
     */
    public stopPolling(): void {
        if (this.pollingInterval) {
            console.log('[GamepadService] Stopping gamepad polling');
            clearInterval(this.pollingInterval);
            this.pollingInterval = null;
        }
    }

    /**
     * Poll current gamepad state
     */
    private pollGamepad(): void {
        const gamepads = navigator.getGamepads();

        if (this.gamepadIndex >= 0 && gamepads[this.gamepadIndex]) {
            const gamepad = gamepads[this.gamepadIndex];
            if (gamepad) {
                this.updateGamepadState(gamepad);
                this.updateGamepadInput(gamepad);
            }
        } else {
            // Check for any connected gamepad
            for (let i = 0; i < gamepads.length; i++) {
                if (gamepads[i]) {
                    this.gamepadIndex = i;
                    console.log('[GamepadService] Auto-detected gamepad at index', i);
                    break;
                }
            }
        }
    }

    /**
     * Update raw gamepad state
     */
    private updateGamepadState(gamepad: Gamepad): void {
        this.gamepadStateSubject.next({
            connected: true,
            id: gamepad.id,
            buttons: gamepad.buttons.map(b => b.pressed),
            axes: gamepad.axes.map(a => a)
        });
    }

    /**
     * Update parsed gamepad input
     */
    private updateGamepadInput(gamepad: Gamepad): void {
        const input: GamepadInput = {
            // Left stick (axes 0, 1) - Roll and Pitch
            leftStickX: this.applyDeadzone(gamepad.axes[0]),
            leftStickY: this.applyDeadzone(gamepad.axes[1]),

            // Right stick (axes 2, 3) - Yaw and Throttle
            rightStickX: this.applyDeadzone(gamepad.axes[2]),
            rightStickY: this.applyDeadzone(gamepad.axes[3]),

            // Buttons (standard mapping)
            buttonA: gamepad.buttons[0]?.pressed ?? false,
            buttonB: gamepad.buttons[1]?.pressed ?? false,
            buttonX: gamepad.buttons[2]?.pressed ?? false,
            buttonY: gamepad.buttons[3]?.pressed ?? false,

            // Bumpers
            leftBumper: gamepad.buttons[4]?.pressed ?? false,
            rightBumper: gamepad.buttons[5]?.pressed ?? false,

            // Triggers (buttons 6, 7 have analog values)
            leftTrigger: gamepad.buttons[6]?.value ?? 0,
            rightTrigger: gamepad.buttons[7]?.value ?? 0
        };

        this.gamepadInputSubject.next(input);
    }

    /**
     * Apply deadzone to axis value
     */
    private applyDeadzone(value: number): number {
        if (Math.abs(value) < this.DEADZONE) {
            return 0;
        }

        // Scale value to account for deadzone
        const sign = value > 0 ? 1 : -1;
        const scaled = (Math.abs(value) - this.DEADZONE) / (1 - this.DEADZONE);
        return sign * scaled;
    }

    /**
     * Check if any gamepad is currently connected
     */
    public isConnected(): boolean {
        return this.gamepadStateSubject.value.connected;
    }

    /**
     * Get current gamepad state
     */
    public getCurrentState(): GamepadState {
        return this.gamepadStateSubject.value;
    }

    /**
     * Get current gamepad input
     */
    public getCurrentInput(): GamepadInput {
        return this.gamepadInputSubject.value;
    }

    /**
     * Get gamepad type/brand from ID
     */
    public getGamepadType(id: string): string {
        const lowerCaseId = id.toLowerCase();

        if (lowerCaseId.includes('xbox')) {
            return 'Xbox Controller';
        } else if (lowerCaseId.includes('playstation') || lowerCaseId.includes('dualshock') || lowerCaseId.includes('dualsense')) {
            return 'PlayStation Controller';
        } else if (lowerCaseId.includes('nintendo') || lowerCaseId.includes('pro controller')) {
            return 'Nintendo Controller';
        } else if (lowerCaseId.includes('logitech')) {
            return 'Logitech Controller';
        } else {
            return 'Generic Controller';
        }
    }

    /**
     * Vibrate gamepad (if supported)
     */
    public vibrate(duration: number = 200, weakMagnitude: number = 0.5, strongMagnitude: number = 0.5): void {
        const gamepads = navigator.getGamepads();

        if (this.gamepadIndex >= 0 && gamepads[this.gamepadIndex]) {
            const gamepad = gamepads[this.gamepadIndex];

            if (gamepad && 'vibrationActuator' in gamepad) {
                const actuator = (gamepad as any).vibrationActuator;
                if (actuator && typeof actuator.playEffect === 'function') {
                    actuator.playEffect('dual-rumble', {
                        duration: duration,
                        weakMagnitude: weakMagnitude,
                        strongMagnitude: strongMagnitude
                    }).catch((err: any) => {
                        console.warn('[GamepadService] Vibration not supported:', err);
                    });
                }
            }
        }
    }

    /**
     * Cleanup on service destroy
     */
    public ngOnDestroy(): void {
        this.stopPolling();
    }
}
