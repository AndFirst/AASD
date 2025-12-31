import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

export type WarningItem = {
  id: string;
  type: 'no_feed' | 'aggression_alert' | 'info';
  title: string;
  message: string;
  ts: number; // Date.now()
};

@Component({
  selector: 'app-warnings',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './warnings.html',
  styleUrls: ['./warnings.css'],
})
export class Warnings {
  @Input({ required: true }) warnings: WarningItem[] = [];

  dismiss(id: string): void {
    this.warnings = this.warnings.filter(w => w.id !== id);
  }

  trackById(_: number, w: WarningItem): string {
    return w.id;
  }

  fmt(ts: number): string {
    return new Date(ts).toLocaleTimeString();
  }
}
