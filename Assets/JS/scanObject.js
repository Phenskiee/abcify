const fileInput = document.getElementById('fileInput');
const imagePreview = document.getElementById('imagePreview');
const video = document.getElementById('video');
const captureButton = document.getElementById('captureButton');
const deleteButton = document.getElementById('deleteButton');
const closeButton = document.getElementById('closeButton');
const predictionResult = document.getElementById('predictionResult');
const uploadButton = document.getElementById('uploadButton');
const cameraButton = document.getElementById('cameraButton');

let usingCamera = false;
let predictionText = '';
let femaleVoice = null

function loadVoices() {
    return new Promise((resolve) => {
        const synth = window.speechSynthesis;
        const voices = synth.getVoices();
        const checkVoices = () => {
            const updatedVoices = synth.getVoices();
            femaleVoice = updatedVoices.find(voice => voice.name.toLowerCase().includes('female')) || updatedVoices.find(voice => voice.name.toLowerCase().includes('female'));
            resolve();
        };
        if (voices.length) {
            checkVoices();
            }
            else {
                synth.onvoiceschanged = checkVoices;
            }
    });
}

async function init() {
    await loadVoices();
}

async function startCamera() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        video.srcObject = stream;
        video.style.display = 'block';
        imagePreview.style.display = 'none';
        captureButton.style.display = 'block';
        deleteButton.style.display = 'none';
        closeButton.style.display = 'block';
        uploadButton.style.display = 'none';
        cameraButton.style.display = 'none';
        speakButton.style.display = 'none';
        usingCamera = true;
    } 
    catch (err) {
        console.error("Error accessing the camera", err);
         alert("Error accessing the camera. Please make sure you have given permission.");
    }
}

function captureImage() {
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d').drawImage(video, 0, 0);
    imagePreview.src = canvas.toDataURL('image/jpeg');
    imagePreview.style.display = 'block';
    video.style.display = 'none';
    captureButton.style.display = 'none';
    deleteButton.style.display = 'block';
    closeButton.style.display = 'none';
    sendImageForPrediction(canvas.toDataURL('image/jpeg'));
}

function deleteImage() {
    imagePreview.src = '';
    imagePreview.style.display = 'none';
    deleteButton.style.display = 'none';
    predictionResult.innerHTML = '';
    speakButton.style.display = 'none';

    if (usingCamera) {
        video.style.display = 'block';
        captureButton.style.display = 'block';
        closeButton.style.display = 'block';
        uploadButton.style.display = 'none';
        cameraButton.style.display = 'none';
    }
    else {
        video.style.display = 'none';
        captureButton.style.display = 'none';
        closeButton.style.display = 'none';
        uploadButton.style.display = 'block';
        cameraButton.style.display = 'block';
    }
}

function closeCamera() {
    stopCamera();
    video.style.display = 'none';
    captureButton.style.display = 'none';
    closeButton.style.display = 'none';
    uploadButton.style.display = 'block';
    cameraButton.style.display = 'block';
    speakButton.style.display = 'none';
    usingCamera = false;
}

function stopCamera() {
    const stream = video.srcObject;
    if (stream) {
        const tracks = stream.getTracks();
        tracks.forEach(track => track.stop());
        video.srcObject = null;
    }
}

async function sendImageForPrediction(imageData) {
    const response = await fetch('/predict', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: `base64Image=${encodeURIComponent(imageData)}`
    });

    const result = await response.json();
    if (result.error) {
        predictionResult.innerHTML = `Error: ${result.error}`;
        speakText(`Error: ${result.error}`);
    }
    else {
        const prediction = result.prediction;
        predictionText = prediction;

        const highlightedResult = `<span class="highlight">${prediction.charAt(0)}</span>${prediction.slice(1)}`;
        predictionResult.innerHTML = `Prediction: ${highlightedResult}`;
        // speakText(`${prediction}`);
        speakButton.style.display = 'block';
    }
}

function handleFileSelect(event) {
    const file = event.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = function(e) {
            imagePreview.src = e.target.result;
            imagePreview.style.display = 'block';
            video.style.display = 'none';
            captureButton.style.display = 'none';
            deleteButton.style.display = 'block';
            closeButton.style.display = 'none';
            uploadButton.style.display = 'none';
            cameraButton.style.display = 'none';
            speakButton.style.display = 'none';
            sendImageForPrediction(e.target.result);
        }
        reader.readAsDataURL(file);
    }
}

function speakText(text) {
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'en-US';
    window.speechSynthesis.speak(utterance);
}
function speakResult() {
    if (predictionText) {
        speakText(`${predictionText}`);
    }
    else {
        speakText("No prediction result available.");
    }
}