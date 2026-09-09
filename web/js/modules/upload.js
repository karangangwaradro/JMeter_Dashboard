// modules/upload.js — File Upload & Drag-and-Drop Ingestion
import { api } from '../core/api.js';
import { loadTests } from './dashboard.js';

export function setupDragAndDrop() {
    const zone = document.getElementById("drop-zone");
    if (!zone) return;

    zone.addEventListener("click", () => document.getElementById("file-input")?.click());

    ["dragenter", "dragover"].forEach(eventName => {
        zone.addEventListener(eventName, e => {
            e.preventDefault();
            zone.classList.add("dragover");
        });
    });

    ["dragleave", "drop"].forEach(eventName => {
        zone.addEventListener(eventName, e => {
            e.preventDefault();
            zone.classList.remove("dragover");
        });
    });

    zone.addEventListener("drop", e => {
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            uploadFile(files[0]);
        }
    });
}

export function handleFileSelect(e) {
    const files = e.target.files;
    if (files && files.length > 0) {
        uploadFile(files[0]);
    }
    e.target.value = "";
}

export async function uploadFile(file) {
    const formData = new FormData();
    formData.append("file", file);

    try {
        const data = await api.upload("/api/upload-jmx", formData);
        alert(data.message);
        loadTests();
    } catch (err) {
        alert("Upload failed: " + err);
    }
}

window.setupDragAndDrop = setupDragAndDrop;
window.handleFileSelect = handleFileSelect;
window.uploadFile = uploadFile;
