class CameraManager {
    constructor(videoElement, cameraUrl) {
        this.videoElement = videoElement;
        this.cameraUrl = cameraUrl;
        this.isPlaying = false;
    }

    async start() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    facingMode: 'environment'
                }
            });
            this.videoElement.srcObject = stream;
            this.isPlaying = true;
            this.videoElement.play();
        } catch (error) {
            console.error('Error accessing camera:', error);
        }
    }

    stop() {
        if (this.isPlaying) {
            const stream = this.videoElement.srcObject;
            const tracks = stream.getTracks();
            tracks.forEach(track => track.stop());
            this.videoElement.srcObject = null;
            this.isPlaying = false;
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const cameraElements = document.querySelectorAll('[data-camera-url]');
    cameraElements.forEach(element => {
        const cameraUrl = element.dataset.cameraUrl;
        const videoElement = element.querySelector('video');
        if (videoElement) {
            const camera = new CameraManager(videoElement, cameraUrl);
            element.dataset.cameraManager = camera;
        }
    });
});
