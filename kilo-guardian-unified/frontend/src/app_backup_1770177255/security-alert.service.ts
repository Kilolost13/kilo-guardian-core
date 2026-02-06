import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, interval, Observable, of } from 'rxjs';
import { tap, catchError, map } from 'rxjs/operators';

export interface SecurityAlert {
  id: string;
  timestamp: string;
  severity: string;
  message: string;
  recommendations: string[];
  source_ip: string;
  dismissed?: boolean;
}

@Injectable({ providedIn: 'root' })
export class SecurityAlertService {
  private alerts$ = new BehaviorSubject<SecurityAlert[]>([]);
  private apiBase = 'http://localhost:8001/api/security';
  private lastFetchTs: string | null = null;

  constructor(private http: HttpClient) {
    // Poll every 5 seconds
    interval(5000)
      .pipe(
        tap(() => this.fetchAlerts().subscribe()),
        catchError((err: any) => {
          console.error('Alert poll error', err);
          return of(null);
        })
      ).subscribe();
    this.fetchAlerts().subscribe();
  }

  getAlerts() {
    return this.alerts$.asObservable();
  }

  fetchAlerts(): Observable<SecurityAlert[]> {
    return this.http.get<{ alerts: SecurityAlert[]; count: number }>(`${this.apiBase}/alerts`).pipe(
      map((res: { alerts: SecurityAlert[]; count: number }) => {
        this.lastFetchTs = new Date().toISOString();
        this.alerts$.next(res.alerts || []);
        return res.alerts || [];
      }),
      catchError((err: any) => {
        console.error('fetchAlerts error', err);
        return of([] as SecurityAlert[]);
      })
    );
  }

  dismissAlert(id: string): Observable<boolean> {
    return this.http.post<{ success: boolean; message: string }>(`${this.apiBase}/alerts/${id}/dismiss`, {}).pipe(
      map((res: { success: boolean }) => {
        if (res.success) {
          const updated = this.alerts$.value.map((a: SecurityAlert) => (a.id === id ? { ...a, dismissed: true } : a));
          this.alerts$.next(updated);
        }
        return res.success;
      }),
      catchError((err: any) => {
        console.error('dismissAlert error', err);
        return of(false);
      })
    );
  }
}
