// core/api.js — Centralized HTTP Client
export const api = {
    async get(url) {
        const res = await fetch(url);
        if (!res.ok) {
            const text = await res.text();
            throw new Error(`GET ${url} returned ${res.status}: ${text}`);
        }
        return await res.json();
    },

    async post(url, body) {
        const res = await fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body)
        });
        if (!res.ok) {
            const text = await res.text();
            throw new Error(`POST ${url} returned ${res.status}: ${text}`);
        }
        return await res.json();
    },

    async upload(url, formData) {
        const res = await fetch(url, {
            method: "POST",
            body: formData
        });
        if (!res.ok) {
            const text = await res.text();
            throw new Error(`Upload to ${url} returned ${res.status}: ${text}`);
        }
        return await res.json();
    }
};
