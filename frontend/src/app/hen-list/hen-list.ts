import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
// ...
export class Hen {
  constructor(
    public id: string,
    public hunger: number,
    public aggression: number,
    public light_level: number,
    public last_update: string
  ) {}
}

@Component({
  selector: 'app-hen-list',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './hen-list.html',
  styleUrl: './hen-list.css',
})
export class HenList {
  @Input({ required: true }) hens: Hen[] = [];

  clamp(v: number): number {
    return Math.max(0, Math.min(100, v));
  }

  aggrWidth(aggr: number | null | undefined): number {
    if (aggr == null || Number.isNaN(aggr)) {
      return 0;
    }

    return Math.min(50, Math.abs(aggr) * 5);
  }

  aggrSide(aggr: number | null | undefined): 'neg' | 'pos' | 'zero' {
    if (!aggr) return 'zero';
    return aggr < 0 ? 'neg' : 'pos';
  }

}
