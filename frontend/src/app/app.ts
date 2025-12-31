import { Component, OnDestroy, OnInit, ChangeDetectorRef, inject } from '@angular/core';
import { Subscription } from 'rxjs';
import { Feeder, FeederState } from './feeder/feeder';
import { HenList, Hen } from './hen-list/hen-list';
import { WsService, WsEvent } from './ws.service';
import {WarningItem, Warnings} from './warnings/warnings';

@Component({
  selector: 'app-root',
  standalone: true,
  templateUrl: 'app.html',
  imports: [ Feeder, HenList, Warnings],
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

  ngOnInit(): void {
    this.ws.connect('ws://localhost:8765');

    this.sub = this.ws.events$.subscribe((evt: WsEvent) => {
      console.log('[WS] Event:', evt);
      if(evt.type !== 'ui_snapshot') {
        return;
      }

      this.hens = this.aggregateHens(
        evt.state.hens,
        evt.state.lights_by_hen
      );
      this.feederState = new FeederState(
        evt.state.feed.capacity,
        evt.state.feed.remaining_feed,
        evt.state.feed.last_update
      )
      console.log(this.feederState);
      this.cdr.markForCheck();
    });

  }

  ngOnDestroy(): void {
    this.sub?.unsubscribe();
  }
}
