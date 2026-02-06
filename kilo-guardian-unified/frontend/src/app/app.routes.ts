import { Routes } from '@angular/router';

export const routes: Routes = [
    { 
        path: 'drone-fpv', 
        loadComponent: () => import('./drone-fpv/drone-fpv.component').then(m => m.DroneFpvComponent) 
    },
    { 
        path: 'mesh-tracker', 
        loadComponent: () => import('./mesh-tracker/mesh-tracker.component').then(m => m.MeshTrackerComponent) 
    }
];
