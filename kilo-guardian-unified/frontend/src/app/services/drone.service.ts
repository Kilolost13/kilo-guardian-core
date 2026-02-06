import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, Subject } from 'rxjs';

export interface TelemetryData {
    altitude: number;
    speed: number;
    heading: number;
    battery: number;
    armed: boolean;
    roll: number;
    pitch: number;
    latitude: number;
    longitude: number;
    satellites: number;
    mode: string;
}

export interface Waypoint {
    lat: number;
    lng: number;
    alt: number;
}

export interface Mission {
    waypoints: Waypoint[];
    missionType: string;
}

@Injectable({
    providedIn: 'root'
})
export class DroneService {
    private wsBaseUrl = 'ws://localhost:8000/api/drone';

    // WebSocket connections
    private videoWs: WebSocket | null = null;
    private telemetryWs: WebSocket | null = null;
    private controlWs: WebSocket | null = null;

    // Observables
    private videoFrameSubject = new Subject<Blob>();
    private telemetrySubject = new BehaviorSubject<TelemetryData>({
        altitude: 0,
        speed: 0,
        heading: 0,
        battery: 100,
        armed: false,
        roll: 0,
        pitch: 0,
        latitude: 0,
        longitude: 0,
        satellites: 0,
        mode: 'STABILIZE'
    });

    private connectionStatusSubject = new BehaviorSubject<string>('disconnected');

    // Public observables
    public videoFrame$ = this.videoFrameSubject.asObservable();
    public telemetry$ = this.telemetrySubject.asObservable();
    public connectionStatus$ = this.connectionStatusSubject.asObservable();

    // Reconnection settings
    private reconnectAttempts = 0;
    private maxReconnectAttempts = 5;
    private reconnectDelay = 2000;

    constructor() {
        console.log('[DroneService] Initialized');
    }

    /**
     * Connect to all drone WebSocket streams
     */
    public connect(): void {
        console.log('[DroneService] Connecting to drone...');
        this.connectionStatusSubject.next('connecting');

        this.connectVideoStream();
        this.connectTelemetryStream();
        this.connectControlStream();
    }

    /**
     * Connect to video stream and return observable
     */
    public connectVideo(): Observable<Blob> {
        this.connectVideoStream();
        return this.videoFrame$;
    }

    /**
     * Connect to telemetry stream and return observable
     */
    public connectTelemetry(): Observable<TelemetryData> {
        this.connectTelemetryStream();
        return this.telemetry$;
    }

    /**
     * Request manual control token (wraps enableManualControl)
     */
    public async requestManualControlToken(): Promise<{ token?: string; success: boolean }> {
        const success = await this.enableManualControl();
        return { success, token: success ? 'granted' : undefined };
    }    /**
     * Disconnect all streams
     */
    public disconnect(): void {
        console.log('[DroneService] Disconnecting from drone...');

        if (this.videoWs) {
            this.videoWs.close();
            this.videoWs = null;
        }

        if (this.telemetryWs) {
            this.telemetryWs.close();
            this.telemetryWs = null;
        }

        if (this.controlWs) {
            this.controlWs.close();
            this.controlWs = null;
        }

        this.connectionStatusSubject.next('disconnected');
        this.reconnectAttempts = 0;
    }

    /**
     * Connect to video stream WebSocket
     */
    private connectVideoStream(): void {
        try {
            this.videoWs = new WebSocket(`${this.wsBaseUrl}/video`);
            this.videoWs.binaryType = 'blob';

            this.videoWs.onopen = () => {
                console.log('[DroneService] Video stream connected');
                this.reconnectAttempts = 0;
            };

            this.videoWs.onmessage = (event) => {
                if (event.data instanceof Blob) {
                    this.videoFrameSubject.next(event.data);
                }
            };

            this.videoWs.onerror = (error) => {
                console.error('[DroneService] Video stream error:', error);
            };

            this.videoWs.onclose = () => {
                console.warn('[DroneService] Video stream closed');
                this.handleReconnect('video');
            };

        } catch (error) {
            console.error('[DroneService] Failed to connect video stream:', error);
            this.handleReconnect('video');
        }
    }

    /**
     * Connect to telemetry stream WebSocket
     */
    private connectTelemetryStream(): void {
        try {
            this.telemetryWs = new WebSocket(`${this.wsBaseUrl}/telemetry`);

            this.telemetryWs.onopen = () => {
                console.log('[DroneService] Telemetry stream connected');
                this.connectionStatusSubject.next('connected');
                this.reconnectAttempts = 0;
            };

            this.telemetryWs.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.telemetrySubject.next(data);
                } catch (error) {
                    console.error('[DroneService] Failed to parse telemetry:', error);
                }
            };

            this.telemetryWs.onerror = (error) => {
                console.error('[DroneService] Telemetry stream error:', error);
            };

            this.telemetryWs.onclose = () => {
                console.warn('[DroneService] Telemetry stream closed');
                this.connectionStatusSubject.next('disconnected');
                this.handleReconnect('telemetry');
            };

        } catch (error) {
            console.error('[DroneService] Failed to connect telemetry stream:', error);
            this.handleReconnect('telemetry');
        }
    }

    /**
     * Connect to manual control stream WebSocket
     */
    private connectControlStream(): void {
        try {
            this.controlWs = new WebSocket(`${this.wsBaseUrl}/manual_control`);

            this.controlWs.onopen = () => {
                console.log('[DroneService] Control stream connected');
            };

            this.controlWs.onerror = (error) => {
                console.error('[DroneService] Control stream error:', error);
            };

            this.controlWs.onclose = () => {
                console.warn('[DroneService] Control stream closed');
                this.handleReconnect('control');
            };

        } catch (error) {
            console.error('[DroneService] Failed to connect control stream:', error);
            this.handleReconnect('control');
        }
    }

    /**
     * Handle reconnection logic
     */
    private handleReconnect(streamType: string): void {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error(`[DroneService] Max reconnect attempts reached for ${streamType}`);
            return;
        }

        this.reconnectAttempts++;
        const delay = this.reconnectDelay * Math.pow(1.5, this.reconnectAttempts - 1);

        console.log(`[DroneService] Reconnecting ${streamType} in ${delay}ms (attempt ${this.reconnectAttempts})`);

        setTimeout(() => {
            switch (streamType) {
                case 'video':
                    this.connectVideoStream();
                    break;
                case 'telemetry':
                    this.connectTelemetryStream();
                    break;
                case 'control':
                    this.connectControlStream();
                    break;
            }
        }, delay);
    }

    /**
     * Send manual control input
     */
    public sendManualControl(x: number, y: number, z: number, r: number): void {
        if (!this.controlWs || this.controlWs.readyState !== WebSocket.OPEN) {
            console.warn('[DroneService] Control WebSocket not connected');
            return;
        }

        const command = {
            type: 'manual_control',
            x: Math.max(-1, Math.min(1, x)),  // Clamp to [-1, 1]
            y: Math.max(-1, Math.min(1, y)),
            z: Math.max(-1, Math.min(1, z)),
            r: Math.max(-1, Math.min(1, r)),
            timestamp: Date.now()
        };

        try {
            this.controlWs.send(JSON.stringify(command));
        } catch (error) {
            console.error('[DroneService] Failed to send manual control:', error);
        }
    }

    /**
     * Enable manual control mode
     */
    public async enableManualControl(): Promise<boolean> {
        try {
            const response = await fetch('http://localhost:8000/api/drone/manual_control/enable', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });

            const result = await response.json();
            console.log('[DroneService] Manual control enable response:', result);
            return result.success === true;

        } catch (error) {
            console.error('[DroneService] Failed to enable manual control:', error);
            return false;
        }
    }

    /**
     * Disable manual control mode
     */
    public async disableManualControl(): Promise<boolean> {
        try {
            const response = await fetch('http://localhost:8000/api/drone/manual_control/disable', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });

            const result = await response.json();
            console.log('[DroneService] Manual control disable response:', result);
            return result.success === true;

        } catch (error) {
            console.error('[DroneService] Failed to disable manual control:', error);
            return false;
        }
    }

    /**
     * Upload mission to drone
     */
    public async uploadMission(mission: Mission): Promise<boolean> {
        try {
            const response = await fetch('http://localhost:8000/api/drone/mission/upload', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(mission)
            });

            const result = await response.json();
            console.log('[DroneService] Mission upload response:', result);
            return result.success === true;

        } catch (error) {
            console.error('[DroneService] Failed to upload mission:', error);
            return false;
        }
    }

    /**
     * Start mission
     */
    public async startMission(): Promise<boolean> {
        try {
            const response = await fetch('http://localhost:8000/api/drone/mission/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });

            const result = await response.json();
            console.log('[DroneService] Start mission response:', result);
            return result.success === true;

        } catch (error) {
            console.error('[DroneService] Failed to start mission:', error);
            return false;
        }
    }

    /**
     * Arm the drone
     */
    public async arm(): Promise<boolean> {
        try {
            const response = await fetch('http://localhost:8000/api/drone/arm', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });

            const result = await response.json();
            console.log('[DroneService] Arm response:', result);
            return result.success === true;

        } catch (error) {
            console.error('[DroneService] Failed to arm:', error);
            return false;
        }
    }

    /**
     * Disarm the drone
     */
    public async disarm(): Promise<boolean> {
        try {
            const response = await fetch('http://localhost:8000/api/drone/disarm', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });

            const result = await response.json();
            console.log('[DroneService] Disarm response:', result);
            return result.success === true;

        } catch (error) {
            console.error('[DroneService] Failed to disarm:', error);
            return false;
        }
    }

    /**
     * Takeoff to specified altitude
     */
    public async takeoff(altitude: number = 10): Promise<boolean> {
        try {
            const response = await fetch('http://localhost:8000/api/drone/takeoff', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ altitude })
            });

            const result = await response.json();
            console.log('[DroneService] Takeoff response:', result);
            return result.success === true;

        } catch (error) {
            console.error('[DroneService] Failed to takeoff:', error);
            return false;
        }
    }

    /**
     * Land the drone
     */
    public async land(): Promise<boolean> {
        try {
            const response = await fetch('http://localhost:8000/api/drone/land', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });

            const result = await response.json();
            console.log('[DroneService] Land response:', result);
            return result.success === true;

        } catch (error) {
            console.error('[DroneService] Failed to land:', error);
            return false;
        }
    }

    /**
     * Return to launch (home)
     */
    public async returnToLaunch(): Promise<boolean> {
        try {
            const response = await fetch('http://localhost:8000/api/drone/rtl', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });

            const result = await response.json();
            console.log('[DroneService] RTL response:', result);
            return result.success === true;

        } catch (error) {
            console.error('[DroneService] Failed to RTL:', error);
            return false;
        }
    }

    /**
     * Get current telemetry snapshot
     */
    public getCurrentTelemetry(): TelemetryData {
        return this.telemetrySubject.value;
    }
}
