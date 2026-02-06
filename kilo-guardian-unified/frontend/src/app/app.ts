import { CommonModule } from '@angular/common';
import { HttpClient, HttpClientModule } from '@angular/common/http';
import { Component, OnInit } from '@angular/core';
import { Router, RouterOutlet } from '@angular/router';
import { BillingPortalComponent } from './billing-portal.component';
import { CommunityComponent } from './community.component';
import { FeaturesComponent } from './features.component';
import { HeroComponent } from './hero.component';
import { MarketplaceComponent } from './marketplace.component';
import { NavSidebarComponent } from './nav-sidebar.component';
import { PluginHealthIndicatorComponent } from './plugin-health-indicator.component';
import { SystemLogComponent } from './system-log.component';
import { VpnDashboardComponent } from './vpn-dashboard.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    CommonModule,
    HttpClientModule,
    RouterOutlet,
    NavSidebarComponent,
    SystemLogComponent,
    HeroComponent,
    FeaturesComponent,
    MarketplaceComponent,
    CommunityComponent,
    VpnDashboardComponent,
    BillingPortalComponent,
    PluginHealthIndicatorComponent
  ],
  templateUrl: './app.html',
  styleUrls: ['./app.css']
})
export class App implements OnInit {
  currentView: string = 'home';
  systemStatus: string = 'GREEN';
  statusMessage: string = 'Initializing...';
  showMarketingSite: boolean = true;

  constructor(private http: HttpClient, private router: Router) {
    // Initial check for current URL
    const initialUrl = this.router.url;
    this.showMarketingSite = !(initialUrl.includes('/drone-fpv') || initialUrl.includes('/mesh-tracker'));

    // Listen for route changes
    this.router.events.subscribe(() => {
      const url = this.router.url;
      this.showMarketingSite = !(url.includes('/drone-fpv') || url.includes('/mesh-tracker'));
    });
  }

  ngOnInit() {
    // Poll system health every 10 seconds (reduced frequency)
    setInterval(() => this.checkHealth(), 10000);
    // Initial check with delay to allow page to load
    setTimeout(() => this.checkHealth(), 1000);
  }

  checkHealth() {
    this.http.get<any>('http://localhost:8001/api/system/health').subscribe({
      next: (data) => {
        this.systemStatus = data.status || 'GREEN';
        this.statusMessage = data.message || 'System Operational';
      },
      error: (err) => {
        // Silently fail - backend is optional for marketing site
        this.systemStatus = 'YELLOW';
        this.statusMessage = 'Demo Mode';
        console.log('Backend offline - running in demo mode');
      }
    });
  }

  onViewChange(view: string) {
    this.currentView = view;
  }
}
