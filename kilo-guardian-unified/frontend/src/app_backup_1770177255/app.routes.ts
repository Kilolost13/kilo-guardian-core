import { Routes } from '@angular/router';
import { DroneFpvComponent } from './drone-fpv/drone-fpv.component';
import { MeshTrackerComponent } from './mesh-tracker/mesh-tracker.component';

export const routes: Routes = [
    { path: 'drone-fpv', component: DroneFpvComponent },
    { path: 'mesh-tracker', component: MeshTrackerComponent }
];

