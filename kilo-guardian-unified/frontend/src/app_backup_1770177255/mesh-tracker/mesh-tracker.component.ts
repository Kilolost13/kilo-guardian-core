import { CommonModule } from '@angular/common';
import { Component, ElementRef, Input, OnDestroy, OnInit, ViewChild } from '@angular/core';

declare const google: any;

export interface MeshDevice {
    id: string;
    name: string;
    latitude: number;
    longitude: number;
    altitude: number;
    battery: number;
    snr: number;
    rssi: number;
    lastSeen: number;
    marker?: any;
}

@Component({
    selector: 'app-mesh-tracker',
    standalone: true,
    imports: [CommonModule],
    templateUrl: './mesh-tracker.component.html',
    styleUrls: ['./mesh-tracker.component.css']
})
export class MeshTrackerComponent implements OnInit, OnDestroy {
    @ViewChild('mapContainer', { static: true }) mapContainer!: ElementRef;
    @Input() overlayMode: boolean = false; // true = overlay on drone map, false = standalone

    private map: any;
    private ws: WebSocket | null = null;
    private devices: Map<string, MeshDevice> = new Map();
    private reconnectAttempts = 0;
    private readonly maxReconnectAttempts = 5;

    public isConnected = false;
    public deviceCount = 0;
    public showDeviceList = true;

    constructor() {
        console.log('[MeshTrackerComponent] Initialized');
    }

    ngOnInit(): void {
        this.initMap();
        this.connectWebSocket();
    }

    ngOnDestroy(): void {
        this.disconnectWebSocket();
    }

    /**
     * Initialize Google Maps
     */
    private initMap(): void {
        if (!this.mapContainer) {
            console.error('[MeshTrackerComponent] Map container not found');
            return;
        }

        const mapOptions = {
            center: { lat: 37.7749, lng: -122.4194 }, // Default: San Francisco
            zoom: 13,
            mapTypeId: google.maps.MapTypeId.HYBRID,
            styles: this.getMapStyles(),
            disableDefaultUI: false,
            zoomControl: true,
            mapTypeControl: true,
            scaleControl: true,
            streetViewControl: false,
            rotateControl: false,
            fullscreenControl: !this.overlayMode
        };

        this.map = new google.maps.Map(this.mapContainer.nativeElement, mapOptions);
        console.log('[MeshTrackerComponent] Map initialized');
    }

    /**
     * Get custom map styles (dark steampunk theme)
     */
    private getMapStyles(): any[] {
        return [
            { elementType: 'geometry', stylers: [{ color: '#1a1a1a' }] },
            { elementType: 'labels.text.stroke', stylers: [{ color: '#000000' }] },
            { elementType: 'labels.text.fill', stylers: [{ color: '#00ff41' }] },
            {
                featureType: 'administrative.locality',
                elementType: 'labels.text.fill',
                stylers: [{ color: '#00ff41' }]
            },
            {
                featureType: 'poi',
                elementType: 'labels.text.fill',
                stylers: [{ color: '#00cc33' }]
            },
            {
                featureType: 'poi.park',
                elementType: 'geometry',
                stylers: [{ color: '#0d3b0d' }]
            },
            {
                featureType: 'road',
                elementType: 'geometry',
                stylers: [{ color: '#2a2a2a' }]
            },
            {
                featureType: 'road',
                elementType: 'geometry.stroke',
                stylers: [{ color: '#1a1a1a' }]
            },
            {
                featureType: 'road',
                elementType: 'labels.text.fill',
                stylers: [{ color: '#00ff41' }]
            },
            {
                featureType: 'road.highway',
                elementType: 'geometry',
                stylers: [{ color: '#3a3a3a' }]
            },
            {
                featureType: 'water',
                elementType: 'geometry',
                stylers: [{ color: '#001a1a' }]
            },
            {
                featureType: 'water',
                elementType: 'labels.text.fill',
                stylers: [{ color: '#00cc99' }]
            }
        ];
    }

    /**
     * Connect to Meshtastic WebSocket
     */
    private connectWebSocket(): void {
        try {
            this.ws = new WebSocket('ws://localhost:8000/api/meshtastic/stream');

            this.ws.onopen = () => {
                console.log('[MeshTrackerComponent] WebSocket connected');
                this.isConnected = true;
                this.reconnectAttempts = 0;
            };

            this.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleMeshEvent(data);
                } catch (error) {
                    console.error('[MeshTrackerComponent] Failed to parse message:', error);
                }
            };

            this.ws.onerror = (error) => {
                console.error('[MeshTrackerComponent] WebSocket error:', error);
            };

            this.ws.onclose = () => {
                console.warn('[MeshTrackerComponent] WebSocket closed');
                this.isConnected = false;
                this.handleReconnect();
            };

        } catch (error) {
            console.error('[MeshTrackerComponent] Failed to connect WebSocket:', error);
            this.handleReconnect();
        }
    }

    /**
     * Disconnect WebSocket
     */
    private disconnectWebSocket(): void {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
        this.isConnected = false;
    }

    /**
     * Handle reconnection logic
     */
    private handleReconnect(): void {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('[MeshTrackerComponent] Max reconnect attempts reached');
            return;
        }

        this.reconnectAttempts++;
        const delay = 2000 * Math.pow(1.5, this.reconnectAttempts - 1);

        console.log(`[MeshTrackerComponent] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);

        setTimeout(() => {
            this.connectWebSocket();
        }, delay);
    }

    /**
     * Handle incoming mesh event
     */
    private handleMeshEvent(data: any): void {
        if (data.type === 'position' && data.device) {
            const device: MeshDevice = {
                id: data.device.id,
                name: data.device.name || `Node ${data.device.id.slice(0, 8)}`,
                latitude: data.device.latitude,
                longitude: data.device.longitude,
                altitude: data.device.altitude || 0,
                battery: data.device.battery || 100,
                snr: data.device.snr || 0,
                rssi: data.device.rssi || 0,
                lastSeen: Date.now()
            };

            this.updateDevice(device);
        } else if (data.type === 'telemetry' && data.device) {
            // Update telemetry for existing device
            const existingDevice = this.devices.get(data.device.id);
            if (existingDevice) {
                existingDevice.battery = data.device.battery || existingDevice.battery;
                existingDevice.snr = data.device.snr || existingDevice.snr;
                existingDevice.rssi = data.device.rssi || existingDevice.rssi;
                existingDevice.lastSeen = Date.now();
            }
        }
    }

    /**
     * Update or add device to map
     */
    private updateDevice(device: MeshDevice): void {
        const existingDevice = this.devices.get(device.id);

        if (existingDevice && existingDevice.marker) {
            // Update existing marker position
            const newPosition = { lat: device.latitude, lng: device.longitude };
            existingDevice.marker.setPosition(newPosition);

            // Update info window content
            existingDevice.marker.infoWindow.setContent(this.getInfoWindowContent(device));

            // Update device data
            Object.assign(existingDevice, device);

        } else {
            // Create new marker
            this.createMarker(device);
            this.devices.set(device.id, device);
            this.deviceCount = this.devices.size;

            // Auto-center on first device
            if (this.devices.size === 1) {
                this.map.setCenter({ lat: device.latitude, lng: device.longitude });
            }
        }
    }

    /**
     * Create marker for device
     */
    private createMarker(device: MeshDevice): void {
        const position = { lat: device.latitude, lng: device.longitude };

        // Custom icon (zombie-green mesh node)
        const icon = {
            path: google.maps.SymbolPath.CIRCLE,
            scale: 8,
            fillColor: '#00ff41',
            fillOpacity: 0.8,
            strokeColor: '#00ff41',
            strokeWeight: 2,
            strokeOpacity: 1
        };

        const marker = new google.maps.Marker({
            position: position,
            map: this.map,
            icon: icon,
            title: device.name,
            animation: google.maps.Animation.DROP
        });

        // Info window
        const infoWindow = new google.maps.InfoWindow({
            content: this.getInfoWindowContent(device)
        });

        marker.addListener('click', () => {
            // Close all other info windows
            this.devices.forEach(d => {
                if (d.marker && d.marker.infoWindow) {
                    d.marker.infoWindow.close();
                }
            });
            infoWindow.open(this.map, marker);
        });

        // Store references
        marker.infoWindow = infoWindow;
        device.marker = marker;
    }

    /**
     * Generate info window content
     */
    private getInfoWindowContent(device: MeshDevice): string {
        const lastSeenMinutes = Math.floor((Date.now() - device.lastSeen) / 60000);
        const batteryColor = device.battery > 50 ? '#00ff41' : device.battery > 20 ? '#ffaa00' : '#ff0000';

        return `
      <div style="font-family: 'Courier New', monospace; color: #00ff41; background: #1a1a1a; padding: 10px; border: 2px solid #00ff41; border-radius: 6px;">
        <h3 style="margin: 0 0 10px 0; color: #00ff41; text-shadow: 0 0 5px rgba(0, 255, 65, 0.5);">
          📡 ${device.name}
        </h3>
        <p style="margin: 5px 0; font-size: 12px;">
          <strong>ID:</strong> ${device.id.slice(0, 12)}...
        </p>
        <p style="margin: 5px 0; font-size: 12px;">
          <strong>Position:</strong> ${device.latitude.toFixed(6)}, ${device.longitude.toFixed(6)}
        </p>
        <p style="margin: 5px 0; font-size: 12px;">
          <strong>Altitude:</strong> ${device.altitude.toFixed(1)} m
        </p>
        <p style="margin: 5px 0; font-size: 12px; color: ${batteryColor};">
          <strong>Battery:</strong> ${device.battery}%
        </p>
        <p style="margin: 5px 0; font-size: 12px;">
          <strong>SNR:</strong> ${device.snr.toFixed(1)} dB
        </p>
        <p style="margin: 5px 0; font-size: 12px;">
          <strong>RSSI:</strong> ${device.rssi} dBm
        </p>
        <p style="margin: 5px 0; font-size: 12px; opacity: 0.7;">
          Last seen: ${lastSeenMinutes === 0 ? 'just now' : lastSeenMinutes + 'm ago'}
        </p>
      </div>
    `;
    }

    /**
     * Get array of devices for display
     */
    public getDeviceArray(): MeshDevice[] {
        return Array.from(this.devices.values())
            .sort((a, b) => b.lastSeen - a.lastSeen);
    }

    /**
     * Center map on specific device
     */
    public centerOnDevice(deviceId: string): void {
        const device = this.devices.get(deviceId);
        if (device) {
            this.map.setCenter({ lat: device.latitude, lng: device.longitude });
            this.map.setZoom(15);

            if (device.marker && device.marker.infoWindow) {
                device.marker.infoWindow.open(this.map, device.marker);
            }
        }
    }

    /**
     * Fit map bounds to show all devices
     */
    public fitAllDevices(): void {
        if (this.devices.size === 0) return;

        const bounds = new google.maps.LatLngBounds();
        this.devices.forEach(device => {
            bounds.extend({ lat: device.latitude, lng: device.longitude });
        });

        this.map.fitBounds(bounds);
    }

    /**
     * Toggle device list visibility
     */
    public toggleDeviceList(): void {
        this.showDeviceList = !this.showDeviceList;
    }

    /**
     * Get battery color for UI
     */
    public getBatteryColor(battery: number): string {
        if (battery > 50) return '#00ff41';
        if (battery > 20) return '#ffaa00';
        return '#ff0000';
    }

    /**
     * Get time since last seen
     */
    public getTimeSince(timestamp: number): string {
        const seconds = Math.floor((Date.now() - timestamp) / 1000);
        if (seconds < 60) return `${seconds}s ago`;

        const minutes = Math.floor(seconds / 60);
        if (minutes < 60) return `${minutes}m ago`;

        const hours = Math.floor(minutes / 60);
        return `${hours}h ago`;
    }
}
