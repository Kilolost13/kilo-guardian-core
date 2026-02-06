import { CommonModule } from '@angular/common';
import { Component, ElementRef, EventEmitter, Input, OnDestroy, OnInit, Output, ViewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Subject } from 'rxjs';
import { DroneService } from '../services/drone.service';

declare const google: any;

interface Waypoint {
    lat: number;
    lon: number;
    alt: number;
    action?: string;
}

interface MissionPreset {
    name: string;
    description: string;
    icon: string;
    action: string;
}

@Component({
    selector: 'app-mission-planner',
    standalone: true,
    imports: [CommonModule, FormsModule],
    templateUrl: './mission-planner.component.html',
    styleUrls: ['./mission-planner.component.css']
})
export class MissionPlannerComponent implements OnInit, OnDestroy {
    @Input() telemetry: any;
    @Output() close = new EventEmitter<void>();
    @ViewChild('mapContainer', { static: false }) mapContainer!: ElementRef;

    private destroy$ = new Subject<void>();
    private map!: any;
    private markers: any[] = [];
    private path!: any;

    waypoints: Waypoint[] = [];
    selectedPreset: string | null = null;
    customAltitude = 20;
    perimeter: 'small' | 'medium' | 'large' = 'medium';

    // Mission presets
    missionPresets: MissionPreset[] = [
        {
            name: 'Perimeter Walk',
            description: 'Patrol around property boundary',
            icon: '🔄',
            action: 'perimeter'
        },
        {
            name: 'Track Target',
            description: 'Follow Meshtastic device (dog collar, etc.)',
            icon: '🎯',
            action: 'track'
        },
        {
            name: 'Check On Me',
            description: 'Schedule periodic check-in at location',
            icon: '⏰',
            action: 'checkin'
        },
        {
            name: 'Area Survey',
            description: 'Scan designated area with grid pattern',
            icon: '📐',
            action: 'survey'
        },
        {
            name: 'Return Home',
            description: 'Immediate return to launch point',
            icon: '🏠',
            action: 'rtl'
        }
    ];

    // Check-in scheduler
    checkinTime = 60; // minutes
    checkinLocation: { lat: number; lon: number } | null = null;

    constructor(private droneService: DroneService) { }

    ngOnInit() {
        this.initializeMap();
    }

    ngOnDestroy() {
        this.destroy$.next();
        this.destroy$.complete();
    }

    // === Map Initialization ===

    initializeMap() {
        const centerLat = this.telemetry?.lat || 47.6062;
        const centerLon = this.telemetry?.lon || -122.3321;

        this.map = new google.maps.Map(this.mapContainer.nativeElement, {
            center: { lat: centerLat, lng: centerLon },
            zoom: 18,
            mapTypeId: 'hybrid', // Satellite view
            styles: [
                {
                    featureType: 'all',
                    elementType: 'labels.text.fill',
                    stylers: [{ color: '#00ff41' }]
                },
                {
                    featureType: 'all',
                    elementType: 'labels.text.stroke',
                    stylers: [{ color: '#000000' }]
                }
            ]
        });

        // Add current drone position marker
        if (this.telemetry?.lat && this.telemetry?.lon) {
            new google.maps.Marker({
                position: { lat: this.telemetry.lat, lng: this.telemetry.lon },
                map: this.map,
                icon: {
                    path: google.maps.SymbolPath.FORWARD_CLOSED_ARROW,
                    scale: 6,
                    fillColor: '#00ff41',
                    fillOpacity: 1,
                    strokeColor: '#000',
                    strokeWeight: 2,
                    rotation: this.telemetry.heading || 0
                },
                title: 'Drone Position'
            });
        }

        // Initialize path polyline
        this.path = new google.maps.Polyline({
            path: [],
            geodesic: true,
            strokeColor: '#00ff41',
            strokeOpacity: 0.8,
            strokeWeight: 3,
            map: this.map
        });

        // Click to add waypoints
        this.map.addListener('click', (event: any) => {
            if (this.selectedPreset === null) {
                this.addWaypoint(event.latLng!.lat(), event.latLng!.lng());
            }
        });
    }

    // === Waypoint Management ===

    addWaypoint(lat: number, lon: number) {
        const waypoint: Waypoint = {
            lat,
            lon,
            alt: this.customAltitude
        };

        this.waypoints.push(waypoint);

        // Add marker
        const marker = new google.maps.Marker({
            position: { lat, lng: lon },
            map: this.map,
            label: {
                text: `${this.waypoints.length}`,
                color: '#00ff41',
                fontWeight: 'bold'
            },
            icon: {
                path: google.maps.SymbolPath.CIRCLE,
                scale: 10,
                fillColor: '#00ff41',
                fillOpacity: 0.6,
                strokeColor: '#00ff41',
                strokeWeight: 2
            }
        });

        marker.addListener('click', () => {
            this.removeWaypoint(this.waypoints.indexOf(waypoint));
        });

        this.markers.push(marker);
        this.updatePath();
    }

    removeWaypoint(index: number) {
        this.waypoints.splice(index, 1);
        this.markers[index].setMap(null);
        this.markers.splice(index, 1);

        // Update marker labels
        this.markers.forEach((marker, i) => {
            marker.setLabel({
                text: `${i + 1}`,
                color: '#00ff41',
                fontWeight: 'bold'
            });
        });

        this.updatePath();
    }

    clearWaypoints() {
        this.waypoints = [];
        this.markers.forEach(marker => marker.setMap(null));
        this.markers = [];
        this.updatePath();
    }

    updatePath() {
        const pathCoords = this.waypoints.map(wp => ({ lat: wp.lat, lng: wp.lon }));
        this.path.setPath(pathCoords);
    }

    // === Mission Presets ===

    selectPreset(preset: MissionPreset) {
        this.selectedPreset = preset.action;
        this.clearWaypoints();

        switch (preset.action) {
            case 'perimeter':
                this.generatePerimeterMission();
                break;
            case 'track':
                this.setupTrackingMission();
                break;
            case 'checkin':
                this.setupCheckinMission();
                break;
            case 'survey':
                this.generateSurveyMission();
                break;
            case 'rtl':
                this.executeRTL();
                break;
        }
    }

    generatePerimeterMission() {
        const centerLat = this.telemetry?.lat || 47.6062;
        const centerLon = this.telemetry?.lon || -122.3321;

        // Calculate perimeter size
        const radiusMap = {
            small: 0.0001,  // ~10m
            medium: 0.0002, // ~20m
            large: 0.0003   // ~30m
        };
        const radius = radiusMap[this.perimeter];

        // Create square perimeter
        const corners = [
            { lat: centerLat + radius, lon: centerLon + radius },
            { lat: centerLat + radius, lon: centerLon - radius },
            { lat: centerLat - radius, lon: centerLon - radius },
            { lat: centerLat - radius, lon: centerLon + radius },
            { lat: centerLat + radius, lon: centerLon + radius } // Close the loop
        ];

        corners.forEach(corner => {
            this.addWaypoint(corner.lat, corner.lon);
        });
    }

    setupTrackingMission() {
        // This would integrate with Meshtastic to track a specific device
        alert('Tracking mission: Select a Meshtastic device from the mesh tracker to follow.');
        // In full implementation, this would:
        // 1. Subscribe to Meshtastic device updates
        // 2. Dynamically update waypoints as device moves
        // 3. Maintain safe following distance
    }

    setupCheckinMission() {
        // Set current location as check-in point
        if (this.telemetry?.lat && this.telemetry?.lon) {
            this.checkinLocation = {
                lat: this.telemetry.lat,
                lon: this.telemetry.lon
            };

            alert(`Check-in scheduled: Drone will return to this location in ${this.checkinTime} minutes.`);

            // In full implementation, this would:
            // 1. Schedule a timer for the specified duration
            // 2. Automatically trigger mission at the scheduled time
            // 3. Return to launch after check-in
        }
    }

    generateSurveyMission() {
        const centerLat = this.telemetry?.lat || 47.6062;
        const centerLon = this.telemetry?.lon || -122.3321;

        // Create grid pattern
        const spacing = 0.00005; // ~5m between lines
        const gridSize = 5; // 5x5 grid

        let direction = 1; // 1 for right, -1 for left (lawnmower pattern)

        for (let row = 0; row < gridSize; row++) {
            const lat = centerLat - (gridSize / 2) * spacing + row * spacing;

            if (direction === 1) {
                // Go right
                for (let col = 0; col < gridSize; col++) {
                    const lon = centerLon - (gridSize / 2) * spacing + col * spacing;
                    this.addWaypoint(lat, lon);
                }
            } else {
                // Go left
                for (let col = gridSize - 1; col >= 0; col--) {
                    const lon = centerLon - (gridSize / 2) * spacing + col * spacing;
                    this.addWaypoint(lat, lon);
                }
            }

            direction *= -1; // Alternate direction
        }
    }

    executeRTL() {
        this.droneService.returnToLaunch().then(() => {
            alert('Return to launch initiated.');
            this.closeModal();
        }).catch(err => {
            alert('RTL failed: ' + err.message);
        });
    }

    // === Mission Execution ===

    async executeMission() {
        if (this.waypoints.length === 0) {
            alert('Please add waypoints or select a mission preset.');
            return;
        }

        try {
            await this.droneService.uploadMission({
                waypoints: this.waypoints.map(wp => ({ lat: wp.lat, lng: wp.lon, alt: wp.alt })),
                missionType: this.selectedPreset || 'manual'
            });
            alert(`Mission uploaded successfully with ${this.waypoints.length} waypoints.`);
            this.closeModal();
        } catch (err: any) {
            alert('Mission upload failed: ' + err.message);
        }
    }

    // === Modal Control ===

    closeModal() {
        this.close.emit();
    }
}
