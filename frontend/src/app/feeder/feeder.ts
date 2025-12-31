import { Component, Input } from '@angular/core';
import {DatePipe} from '@angular/common';

export class FeederState {
  constructor(
    public capacity: number,        // np. 1000
    public remaining_feed: number,  // np. 500
    public last_update: string      // ISO datetime
  ) {}
}

@Component({
  selector: 'app-feeder',
  standalone: true,
  templateUrl: './feeder.html',
  styleUrl: './feeder.css',
  imports: [
    DatePipe
  ]
})
export class Feeder {
  @Input({ required: true }) feeder!: FeederState;

  get capacity(): number {
    return Math.max(0, this.feeder?.capacity ?? 0);
  }

  get level(): number {
    return Math.max(0, this.feeder?.remaining_feed ?? 0);
  }

  get pct(): number {
    const cap = this.capacity;
    const lvl = Math.max(0, Math.min(this.level, cap));
    return cap === 0 ? 0 : Math.round((lvl / cap) * 100);
  }

  get safeLevel(): number {
    const cap = this.capacity;
    return Math.max(0, Math.min(this.level, cap));
  }

  get lastUpdateMs(): number | null {
    const s = this.feeder?.last_update;
    const t = s ? Date.parse(s) : NaN;
    return Number.isFinite(t) ? t : null;
  }
}
