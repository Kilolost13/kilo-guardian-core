import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { SecurityAlertService, SecurityAlert } from './security-alert.service';

@Component({
  selector: 'app-security-alert-banner',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './security-alert-banner.component.html',
  styleUrls: ['./security-alert-banner.component.css']
})
export class SecurityAlertBannerComponent implements OnInit {
  alerts: SecurityAlert[] = [];
  marqueeText = '';

  constructor(private alertService: SecurityAlertService) {}

  ngOnInit() {
    this.alertService.getAlerts().subscribe(alerts => {
      this.alerts = alerts.filter(a => !a.dismissed);
      this._buildMarquee();
    });
  }

  dismiss(alert: SecurityAlert) {
    this.alertService.dismissAlert(alert.id).subscribe();
  }

  severityClass(alert: SecurityAlert) {
    switch (alert.severity) {
      case 'critical': return 'critical';
      case 'warning': return 'warning';
      default: return 'info';
    }
  }

  private _buildMarquee() {
    if (this.alerts.length === 0) {
      this.marqueeText = '';
      return;
    }
    this.marqueeText = this.alerts.map(a => `[${a.severity.toUpperCase()}] ${a.message}`).join('   •   ');
  }
}
