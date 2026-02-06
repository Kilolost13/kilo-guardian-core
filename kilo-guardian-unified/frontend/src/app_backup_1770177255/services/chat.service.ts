import { HttpClient, HttpResponse } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, map } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class ChatService {
    private base = 'http://localhost:8001';

    constructor(private http: HttpClient) { }

    // Sends a chat query and returns either JSON object or plain string depending on Content-Type
    sendQuery(query: string): Observable<any> {
        const url = `${this.base}/api/chat`;
        return this.http
            .post(url, { query }, { observe: 'response', responseType: 'text' as 'json' })
            .pipe(
                map((res: HttpResponse<any>) => {
                    const contentType = res.headers.get('content-type') || '';
                    const text = res.body as string;
                    if (contentType.includes('application/json')) {
                        try {
                            return JSON.parse(text);
                        } catch (e) {
                            return { error: 'Invalid JSON returned from server', raw: text };
                        }
                    }
                    // Return plain string if not JSON
                    return text;
                })
            );
    }
}
