import { Injectable, NgZone, inject } from '@angular/core';
import { Subject, interval, Subscription } from 'rxjs';
export type IsoUtcString = string; // e.g. "2025-12-31T08:27:28.853479+00:00"

export type HenId = string; // e.g. "simulator4@localhost"

export type HenState = {
  hunger: number;
  aggression: number;
  last_update: IsoUtcString;
};

export type FeedState = {
  capacity: number;
  remaining_feed: number;
  last_action: string | null; // "state_update" | "feed_dispensed" | ...
  last_update: IsoUtcString;
  hen_id?: HenId | null;
  portion?: number | null;
  hunger_before?: number | null;
};

export type LightEntry = {
  level: number;
  reason?: string;
  hen_id?: HenId;
  last_update: IsoUtcString;
};

export type UiState = {
  feed: FeedState;
  light: Record<string, never> | Record<string, unknown>; // u Ciebie obecnie {}
  lights_by_hen: Record<HenId, LightEntry>;
  hens: Record<HenId, HenState>;
};

/** Eventy w "events": obecnie zawsze type="critical_event" */
export type CriticalEvent =
  | {
  ts: IsoUtcString;
  sender: string;
  type: "critical_event";
  payload: {
    event: "no_feed";
    hen_id: HenId;
    hunger: number;
    remaining_feed: number;
    // czasem możesz dorzucić threshold itd, więc zostawiamy miejsce:
    [k: string]: unknown;
  };
}
  | {
  ts: IsoUtcString;
  sender: string;
  type: "critical_event";
  payload: {
    event: "aggression_alert";
    hen_id: HenId;
    aggression: number;
    hunger?: number;
    threshold: number;
    [k: string]: unknown;
  };
}
  | {
  ts: IsoUtcString;
  sender: string;
  type: "critical_event";
  payload: {
    event: string; // fallback na przyszłe krytyczne eventy
    [k: string]: unknown;
  };
};

export type UiSnapshotMessage = {
  type: "ui_snapshot";
  ts: IsoUtcString;
  state: UiState;
  events: CriticalEvent[];
};

/** Jeśli WS może wysyłać też inne typy wiadomości niż snapshot */
export type WsEvent = UiSnapshotMessage;


@Injectable({ providedIn: 'root' })
export class WsService {
  private zone = inject(NgZone);

  private socket?: WebSocket;
  private mockSub?: Subscription;

  private eventsSubject = new Subject<WsEvent>();
  readonly events$ = this.eventsSubject.asObservable();

  connect(url: string): void {
    if (this.socket && this.socket.readyState <= 1) return; // CONNECTING/OPEN

    this.socket = new WebSocket(url);

    this.socket.addEventListener('open', () => console.log('[WS] connected'));
    this.socket.addEventListener('close', () => console.log('[WS] disconnected'));
    this.socket.addEventListener('error', (e: Event) => console.error('[WS] error', e));

    this.socket.addEventListener('message', (msg: MessageEvent) => {
      try {
        const data = JSON.parse(String(msg.data)) as WsEvent;
        this.zone.run(() => this.eventsSubject.next(data));
      } catch {
        console.warn('[WS] non-json message:', msg.data);
      }
    });
  }

}
