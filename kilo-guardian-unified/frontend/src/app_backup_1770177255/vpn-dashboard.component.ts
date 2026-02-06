import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient, HttpClientModule } from '@angular/common/http';

@Component({
  selector: 'app-vpn-dashboard',
  standalone: true,
  imports: [CommonModule, HttpClientModule],
  template: `
    <div class="h-full w-full p-4 md:p-6 lg:p-8 grid-bg overflow-y-auto">
      <div class="max-w-7xl mx-auto w-full">
        <h2 class="text-3xl md:text-4xl font-header text-white mb-2">VPN Control Center</h2>
        <p class="text-gray-400 mb-6 md:mb-8 border-l-2 border-[#39ff14] pl-4 text-sm md:text-base">Manage your secure connections</p>

        <div class="grid grid-cols-1 lg:grid-cols-3 gap-4 md:gap-6 mb-6 md:mb-8">
          <!-- License Status Card -->
          <div class="border border-[#39ff14] p-5 md:p-6 bg-black neon-border">
            <div class="flex items-center justify-between mb-4">
              <h3 class="text-lg md:text-xl font-header text-white">License</h3>
              <span class="text-[#39ff14] font-bold text-sm md:text-base">{{ licenseStatus.tier }}</span>
            </div>
            <div class="space-y-2 text-sm">
              <div class="flex justify-between text-gray-400">
                <span>VPN Peers:</span>
                <span class="text-white">{{ licenseStatus.peers_used }} / {{ licenseStatus.peers_limit }}</span>
              </div>
              <div class="flex justify-between text-gray-400">
                <span>Data Transfer:</span>
                <span class="text-white">{{ licenseStatus.data_used_gb }} GB</span>
              </div>
              <div class="flex justify-between text-gray-400">
                <span>Status:</span>
              <span class="text-[#39ff14]">{{ licenseStatus.status }}</span>
            </div>
          </div>
          <button *ngIf="licenseStatus.tier === 'FREE'" 
                  class="w-full mt-4 bg-[#39ff14] text-black font-bold py-2 uppercase hover:bg-white transition-colors">
            Upgrade to Pro
          </button>
        </div>

        <!-- Active Peers Card -->
        <div class="border border-gray-800 p-6 bg-[#0a0a0a]">
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-xl font-header text-white">Active Peers</h3>
            <svg class="text-[#39ff14] animate-pulse" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <polyline points="12 6 12 12 16 14"/>
            </svg>
          </div>
          <div class="text-4xl font-header text-[#39ff14] mb-2">{{ peers.length }}</div>
          <p class="text-gray-400 text-sm">Connected devices</p>
        </div>

        <!-- Quick Actions Card -->
        <div class="border border-gray-800 p-6 bg-[#0a0a0a]">
          <h3 class="text-xl font-header text-white mb-4">Quick Actions</h3>
          <div class="space-y-2">
            <button class="w-full bg-gray-800 hover:bg-[#39ff14] hover:text-black text-white px-4 py-2 text-sm uppercase font-bold transition-colors">
              Add New Peer
            </button>
            <button class="w-full bg-gray-800 hover:bg-[#39ff14] hover:text-black text-white px-4 py-2 text-sm uppercase font-bold transition-colors">
              View QR Codes
            </button>
            <button class="w-full bg-gray-800 hover:bg-[#39ff14] hover:text-black text-white px-4 py-2 text-sm uppercase font-bold transition-colors">
              Download Config
            </button>
          </div>
        </div>
      </div>

      <!-- Peers List -->
      <div class="bg-[#0a0a0a] border border-gray-800">
        <div class="bg-gray-900 px-4 py-2 border-b border-gray-800">
          <span class="text-[#39ff14] font-bold">ACTIVE VPN PEERS</span>
        </div>
        
        <div *ngIf="peers.length === 0" class="p-8 text-center text-gray-400">
          <svg class="mx-auto mb-4 text-gray-600" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="2" y="7" width="20" height="14" rx="2" ry="2"/>
            <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/>
          </svg>
          <p>No peers configured yet.</p>
          <button class="mt-4 bg-[#39ff14] text-black px-6 py-2 font-bold uppercase hover:bg-white transition-colors">
            Add Your First Peer
          </button>
        </div>

        <div *ngFor="let peer of peers" 
             class="p-4 border-b border-gray-800 hover:bg-gray-900 flex justify-between items-center">
          <div>
            <h4 class="text-white font-bold">{{ peer.name }}</h4>
            <p class="text-xs text-gray-500 mt-1">{{ peer.publicKey.substring(0, 32) }}...</p>
          </div>
          <div class="flex gap-2">
            <button class="bg-gray-800 hover:bg-[#39ff14] hover:text-black text-white px-3 py-1 text-xs uppercase font-bold transition-colors">
              QR Code
            </button>
            <button class="bg-gray-800 hover:bg-red-500 hover:text-white text-white px-3 py-1 text-xs uppercase font-bold transition-colors">
              Remove
            </button>
          </div>
        </div>
      </div>
    </div>
  `
})
export class VpnDashboardComponent implements OnInit {
  licenseStatus = {
    tier: 'FREE',
    status: 'ACTIVE',
    peers_used: 0,
    peers_limit: 1,
    data_used_gb: 0
  };

  peers: any[] = [];

  constructor(private http: HttpClient) {}

  ngOnInit() {
    // Fetch license status from API
    this.http.get<any>('http://localhost:8001/api/license/status').subscribe({
      next: (data) => {
        this.licenseStatus = data;
      },
      error: () => {
        // Use default values if API unavailable
      }
    });

    // Fetch peers from API
    this.http.get<any>('http://localhost:8001/api/vpn/server/peers').subscribe({
      next: (data) => {
        this.peers = data.peers || [];
      },
      error: () => {
        // Use empty list if API unavailable
      }
    });
  }
}
