import { CommonModule } from '@angular/common';
import { HttpClientModule } from '@angular/common/http';
import { Component, OnDestroy, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Subscription } from 'rxjs';
import { PluginHealthItem, PluginHealthService, PluginHealthSummary } from './services/plugin-health.service';

@Component({
    selector: 'app-plugin-health-indicator',
    standalone: true,
    imports: [CommonModule, HttpClientModule, FormsModule],
    templateUrl: './plugin-health-indicator.component.html',
    styleUrls: ['./plugin-health-indicator.component.css']
})
export class PluginHealthIndicatorComponent implements OnInit, OnDestroy {
    summary: PluginHealthSummary | null = null;
    loading = false;
    error: string | null = null;
    modalOpen = false;
    filterUnhealthy = false;
    isolationFilter: string | null = null;
    searchQuery = '';
    private sub?: Subscription;

    constructor(private healthSvc: PluginHealthService) { }

    ngOnInit(): void {
        this.loading = true;
        this.sub = this.healthSvc.poll(15000).subscribe({
            next: (data: PluginHealthSummary) => {
                this.summary = data;
                this.loading = false;
                this.error = null;
            },
            error: (_err: unknown) => {
                this.error = 'Health endpoint unavailable';
                this.loading = false;
            }
        });
    }

    ngOnDestroy(): void {
        this.sub?.unsubscribe();
    }

    get lightColor(): 'green' | 'yellow' | 'red' {
        if (!this.summary) return 'yellow';
        if (!this.summary.sandbox_enabled) return 'red';
        if ((this.summary.unhealthy || 0) > 0) return 'yellow';
        return 'green';
    }

    toggleModal(): void {
        if (this.loading && !this.summary) return;
        this.modalOpen = !this.modalOpen;
    }

    pluginStatus(p: PluginHealthItem): 'green' | 'yellow' | 'red' {
        if (!p.healthy) return 'red';
        return 'green';
    }

    isolationLabel(p: PluginHealthItem): string {
        if (!p.sandboxed) return 'none';
        return p.isolation_mode || 'thread';
    }

    trackByName(_idx: number, item: PluginHealthItem) {
        return item.name;
    }

    get filteredPlugins(): PluginHealthItem[] {
        if (!this.summary?.plugins) return [];
        let result = this.summary.plugins;
        if (this.filterUnhealthy) {
            result = result.filter(p => !p.healthy);
        }
        if (this.isolationFilter) {
            result = result.filter(p => this.isolationLabel(p) === this.isolationFilter);
        }
        if (this.searchQuery) {
            const q = this.searchQuery.toLowerCase();
            result = result.filter(p => p.name.toLowerCase().includes(q));
        }
        return result;
    }

    resetHealth(pluginName: string): void {
        this.healthSvc.resetHealth(pluginName).subscribe({
            next: () => {
                // Refresh data after reset
                this.healthSvc.fetchHealth().subscribe((data: PluginHealthSummary) => {
                    this.summary = data;
                });
            },
            error: (_err: unknown) => {
                console.error('Failed to reset health:', _err);
            }
        });
    }
}
