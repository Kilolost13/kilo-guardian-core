import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient, HttpClientModule } from '@angular/common/http';

@Component({
  selector: 'app-billing-portal',
  standalone: true,
  imports: [CommonModule, HttpClientModule],
  template: `
    <div class="h-full w-full p-4 md:p-6 lg:p-8 grid-bg overflow-y-auto">
      <div class="max-w-7xl mx-auto w-full">
        <h2 class="text-3xl md:text-4xl font-header text-white mb-2">Billing Portal</h2>
        <p class="text-gray-400 mb-6 md:mb-8 border-l-2 border-[#39ff14] pl-4 text-sm md:text-base">Manage your subscription and usage</p>

        <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6 mb-6 md:mb-8">
          <!-- Current Plan Card -->
          <div class="border border-[#39ff14] p-5 md:p-6 bg-black neon-border">
            <h3 class="text-lg md:text-xl font-header text-white mb-4">Current Plan</h3>
            <div class="flex items-baseline mb-4">
              <span class="text-3xl md:text-4xl font-header text-[#39ff14]">{{ currentPlan.name }}</span>
              <span class="text-gray-400 ml-2 text-sm md:text-base">{{ currentPlan.price }}</span>
            </div>
            <div class="space-y-2 text-sm text-gray-400 mb-4">
              <div class="flex items-center">
                <svg class="mr-2 text-[#39ff14]" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="20 6 9 17 4 12"/>
                </svg>
                {{ currentPlan.features.peers }} VPN Peers
              </div>
              <div class="flex items-center">
                <svg class="mr-2 text-[#39ff14]" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="20 6 9 17 4 12"/>
              </svg>
              {{ currentPlan.features.routing }}
            </div>
            <div class="flex items-center">
              <svg class="mr-2 text-[#39ff14]" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="20 6 9 17 4 12"/>
              </svg>
              {{ currentPlan.features.qr }}
            </div>
          </div>
          <div class="flex gap-2">
            <button *ngIf="currentPlan.name !== 'Business'" 
                    class="flex-1 bg-[#39ff14] text-black font-bold py-2 uppercase hover:bg-white transition-colors">
              Upgrade
            </button>
            <button *ngIf="currentPlan.name !== 'Free'" 
                    class="flex-1 bg-gray-800 text-white font-bold py-2 uppercase hover:bg-red-500 transition-colors">
              Cancel
            </button>
          </div>
        </div>

        <!-- Usage Summary Card -->
        <div class="border border-gray-800 p-6 bg-[#0a0a0a]">
          <h3 class="text-xl font-header text-white mb-4">This Month's Usage</h3>
          <div class="space-y-4">
            <div>
              <div class="flex justify-between text-sm mb-1">
                <span class="text-gray-400">VPN Peers</span>
                <span class="text-white">{{ usage.peers_used }} / {{ usage.peers_limit }}</span>
              </div>
              <div class="w-full bg-gray-900 h-2 rounded-full overflow-hidden">
                <div class="bg-[#39ff14] h-full" 
                     [style.width.%]="(usage.peers_used / usage.peers_limit) * 100"></div>
              </div>
            </div>

            <div>
              <div class="flex justify-between text-sm mb-1">
                <span class="text-gray-400">Data Transfer</span>
                <span class="text-white">{{ usage.data_used_gb }} GB</span>
              </div>
              <div class="w-full bg-gray-900 h-2 rounded-full overflow-hidden">
                <div class="bg-[#39ff14] h-full" 
                     [style.width.%]="Math.min((usage.data_used_gb / 100) * 100, 100)"></div>
              </div>
            </div>

            <div>
              <div class="flex justify-between text-sm mb-1">
                <span class="text-gray-400">API Calls</span>
                <span class="text-white">{{ usage.api_calls }} / {{ usage.api_calls_limit }}</span>
              </div>
              <div class="w-full bg-gray-900 h-2 rounded-full overflow-hidden">
                <div class="bg-[#39ff14] h-full" 
                     [style.width.%]="(usage.api_calls / usage.api_calls_limit) * 100"></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Pricing Plans -->
      <div class="mb-8">
        <h3 class="text-2xl font-header text-white mb-4">Available Plans</h3>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div *ngFor="let plan of plans" 
               [class]="'border p-6 bg-black ' + (plan.popular ? 'border-[#39ff14] neon-border' : 'border-gray-800')">
            <div *ngIf="plan.popular" class="text-xs bg-[#39ff14] text-black px-2 py-1 inline-block mb-2 font-bold">
              MOST POPULAR
            </div>
            <h4 class="text-2xl font-header text-white mb-2">{{ plan.name }}</h4>
            <div class="text-3xl font-header text-[#39ff14] mb-4">{{ plan.price }}</div>
            <ul class="space-y-2 text-sm text-gray-400 mb-6">
              <li *ngFor="let feature of plan.featureList" class="flex items-start">
                <svg class="mr-2 mt-0.5 text-[#39ff14] flex-shrink-0" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="20 6 9 17 4 12"/>
                </svg>
                <span>{{ feature }}</span>
              </li>
            </ul>
            <button [class]="plan.popular ? 
                    'w-full bg-[#39ff14] text-black font-bold py-3 uppercase hover:bg-white transition-colors' :
                    'w-full bg-gray-800 text-white font-bold py-3 uppercase hover:bg-[#39ff14] hover:text-black transition-colors'">
              {{ plan.name === currentPlan.name ? 'Current Plan' : 'Select Plan' }}
            </button>
          </div>
        </div>
      </div>

      <!-- Payment Method -->
      <div class="border border-gray-800 p-6 bg-[#0a0a0a]">
        <h3 class="text-xl font-header text-white mb-4">Payment Method</h3>
        <div class="flex items-center justify-between">
          <div class="flex items-center">
            <div class="w-12 h-8 bg-gray-800 rounded mr-3 flex items-center justify-center">
              <svg width="24" height="16" viewBox="0 0 24 16" fill="none">
                <rect width="24" height="16" rx="2" fill="#4A5568"/>
                <rect x="2" y="2" width="20" height="3" fill="#CBD5E0"/>
              </svg>
            </div>
            <div>
              <p class="text-white font-bold">•••• •••• •••• 4242</p>
              <p class="text-xs text-gray-500">Expires 12/2025</p>
            </div>
          </div>
          <button class="bg-gray-800 hover:bg-[#39ff14] hover:text-black text-white px-4 py-2 text-sm uppercase font-bold transition-colors">
            Update
          </button>
        </div>
      </div>
      </div>
    </div>
  `
})
export class BillingPortalComponent implements OnInit {
  Math = Math;
  
  currentPlan = {
    name: 'Free',
    price: '$0/month',
    features: {
      peers: '1',
      routing: 'Basic routing',
      qr: 'No QR codes'
    }
  };

  usage = {
    peers_used: 0,
    peers_limit: 1,
    data_used_gb: 0,
    api_calls: 0,
    api_calls_limit: 1000
  };

  plans = [
    {
      name: 'Free',
      price: '$0/month',
      popular: false,
      featureList: [
        '1 VPN Peer',
        'Basic features only',
        'No VPN client routing',
        'No QR codes',
        '1,000 API calls/day'
      ]
    },
    {
      name: 'Pro',
      price: '$4.99/month',
      popular: true,
      featureList: [
        '5 VPN Peers',
        'VPN client routing',
        'QR code generation',
        'Usage analytics',
        '10,000 API calls/day'
      ]
    },
    {
      name: 'Business',
      price: '$14.99/month',
      popular: false,
      featureList: [
        'Unlimited VPN Peers',
        'VPS bridge relay',
        'Advanced analytics',
        'Priority support',
        'Unlimited API calls'
      ]
    }
  ];

  constructor(private http: HttpClient) {}

  ngOnInit() {
    // Fetch billing info from API
    this.http.get<any>('http://localhost:8001/api/billing/summary').subscribe({
      next: (data) => {
        if (data.subscription) {
          this.currentPlan = {
            name: data.subscription.tier,
            price: data.subscription.price,
            features: data.subscription.features
          };
        }
        if (data.usage) {
          this.usage = data.usage;
        }
      },
      error: () => {
        // Use default values if API unavailable
      }
    });
  }
}
