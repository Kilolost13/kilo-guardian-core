import { Component, ViewChild, ElementRef, OnInit } from '@angular/core';
import { HttpClient, HttpClientModule } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-setup-wizard',
  standalone: true,
  imports: [CommonModule, HttpClientModule, FormsModule],
  templateUrl: './setup-wizard.component.html',
  styleUrls: ['./setup-wizard.component.css']
})
export class SetupWizardComponent implements OnInit {
  step = 1;
  userData = {
    name: '',
    aiName: 'Kilo',
    interests: '',
    householdSize: 1,
    location: { lat: 0, lon: 0 },
    faceData: '' // Base64 string
  };
  
  photoCaptured = false;
  @ViewChild('videoElement') videoElement: any;
  @ViewChild('canvasElement') canvasElement: any;

  constructor(private http: HttpClient) {}

  ngOnInit() {
    this.startCamera();
  }

  startCamera() {
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
      navigator.mediaDevices.getUserMedia({ video: true }).then(stream => {
        this.videoElement.nativeElement.srcObject = stream;
        this.videoElement.nativeElement.play();
      });
    }
  }

  capturePhoto() {
    const video = this.videoElement.nativeElement;
    const canvas = this.canvasElement.nativeElement;
    
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d').drawImage(video, 0, 0);
    
    // Save as Base64 for sending to Python backend
    this.userData.faceData = canvas.toDataURL('image/png');
    this.photoCaptured = true;
  }

  detectLocation() {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(position => {
        this.userData.location = {
          lat: position.coords.latitude,
          lon: position.coords.longitude
        };
      });
    }
  }

  nextStep() { this.step++; }

  finishSetup() {
    console.log('finishSetup() called. userData:', this.userData);
    // Send all this data to the backend
    this.http.post('http://localhost:8001/api/setup/initialize', this.userData)
      .subscribe(
        res => {
          console.log('System Initialized - Success:', res);
          // Redirect to main dashboard
        },
        error => {
          console.error('System Initialized - Error:', error);
        }
      );
  }
}
