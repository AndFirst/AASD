import {ChangeDetectorRef, Component, inject, OnDestroy, OnInit} from '@angular/core';
import {Subscription} from 'rxjs';
import {Feeder, FeederState} from './feeder/feeder';
import {Hen, HenList} from './hen-list/hen-list';
import {WsEvent, WsService} from './ws.service';
import {WarningItem, Warnings} from './warnings/warnings';

@Component({
  selector: 'app-root',
  standalone: true,
  templateUrl: 'app.html',
  imports: [Feeder, HenList, Warnings],
})
export class App implements OnInit, OnDestroy {
  private ws = inject(WsService);
  private cdr = inject(ChangeDetectorRef);
  private sub?: Subscription;

  hens: Hen[] = [];

  warnings: WarningItem[] = [];
  feederState: FeederState = new FeederState(0, 0, new Date().toDateString());

  private aggregateHens(
    hens: Record<string, { hunger: number; aggression: number; last_update: string }>,
    lights: Record<string, { level: number; last_update: string }>
  ): Hen[] {
    const ids = new Set([
      ...Object.keys(hens ?? {}),
      ...Object.keys(lights ?? {}),
    ]);

    const result: Hen[] = [];

    for (const id of ids) {
      const hen = hens?.[id];
      const light = lights?.[id];

      const lastUpdate = [hen?.last_update, light?.last_update]
        .filter(Boolean)
        .sort()
        .at(-1)!;

      result.push(
        new Hen(
          id,
          hen?.hunger ?? 0,
          hen?.aggression ?? 0,
          light?.level ?? null,
          lastUpdate
        )
      );
    }

    return result;
  }

  private toWarning(ev: any): WarningItem {
    const payload = ev?.payload ?? {};
    const eventName = payload?.event ?? ev?.type ?? 'event';
    const typeMap = new Map<string, string>([
      ["low_feed_warning", "Mało paszy"],
      ["aggression_alert", "Wykryto agresję"],
      ["no_feed", "Brak paszy"],
    ]);
    let message = "";
    if (eventName == 'low_feed_warning') {
      message = "Niski poziom paszy w zbiorniku.";
    }

    if (eventName == 'aggression_alert') {
      message = "Kura " + payload["hen_id"] + " jest agresywna.";
    }

    if (eventName == 'no_feed') {
      message = "Nie udało się nakarmić kury " + payload["hen_id"] + " - brak paszy w zbiorniku.";
    }
    return {
      ts: ev.ts,
      title: typeMap.get(eventName),
      message: message
    } as any;
  }

  private pushWarnings(items: any[]) {
    if (!items?.length) return;
    const mapped = items.map((x) => this.toWarning(x));

    this.warnings = [...mapped, ...this.warnings].slice(0, 200);
  }

  ngOnInit(): void {
    this.ws.connect('ws://localhost:8765');

    this.sub = this.ws.events$.subscribe((evt: WsEvent) => {
      console.log('[WS] Event:', evt);

      if (evt.type === 'ui_snapshot') {
        this.hens = this.aggregateHens(
          evt.state.hens,
          evt.state.lights_by_hen
        );

        this.feederState = new FeederState(
          evt.state.feed.capacity,
          evt.state.feed.remaining_feed,
          evt.state.feed.last_update
        );

        this.pushWarnings(evt.events as any[]);

        this.cdr.markForCheck();
        return;
      }

      if (evt.type === 'ui_event') {
        this.pushWarnings([evt.event]);
        this.cdr.markForCheck();
        return;
      }
    });
  }

  ngOnDestroy(): void {
    this.sub?.unsubscribe();
  }
}
