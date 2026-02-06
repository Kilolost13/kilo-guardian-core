import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, timer } from 'rxjs';
import { shareReplay, switchMap } from 'rxjs/operators';

export interface PluginHealthDetail {
    status?: string;
    detail?: string;
    last_error?: string;
    failure_count?: number;
    last_execution_time?: number;
    isolation_mode?: string;
    [key: string]: any;
}

export interface PluginHealthItem {
    name: string;
    sandboxed: boolean;
    isolation_mode?: string | null;
    healthy: boolean;
    detail?: PluginHealthDetail;
}

export interface PluginHealthSummary {
    sandbox_enabled: boolean;
    total: number;
    healthy: number;
    unhealthy: number;
    plugins: PluginHealthItem[];
}

@Injectable({ providedIn: 'root' })
export class PluginHealthService {
    private readonly baseUrl = 'http://localhost:8002';
    private readonly endpoint = `${this.baseUrl}/api/plugins/health`;

    constructor(private http: HttpClient) { }

    fetchHealth(): Observable<PluginHealthSummary> {
        return this.http.get<PluginHealthSummary>(this.endpoint);
    }

    // Shared polling stream for components to subscribe to
    poll(intervalMs = 15000): Observable<PluginHealthSummary> {
        return timer(0, intervalMs).pipe(
            switchMap(() => this.fetchHealth()),
            shareReplay(1)
        );
    }

    resetHealth(pluginName: string): Observable<any> {
        return this.http.post(`${this.baseUrl}/api/sandbox/reset/${pluginName}`, {});
    }
}
