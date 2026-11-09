import { readFile } from "node:fs/promises";
import path from "node:path";

const aiServiceUrl = (process.env.AI_SERVICE_URL || "http://127.0.0.1:8000")
    .replace(/\/+$/, "");

export const requestAiDocument = async (document, endpoint, fields = {}) => {
    const uploadDirectory = path.resolve(
        process.env.UPLOAD_DIR || path.join(process.cwd(), "uploads")
    );
    const storedName = path.basename(document.storedName);
    if (storedName !== document.storedName) {
        throw new Error("Invalid stored document path");
    }

    const filePath = path.join(uploadDirectory, storedName);
    const fileBuffer = await readFile(filePath);
    const formData = new FormData();
    formData.append(
        "file",
        new Blob([fileBuffer], { type: document.mimeType || "application/octet-stream" }),
        document.originalName
    );
    for (const [name, value] of Object.entries(fields)) {
        formData.append(name, value);
    }

    const response = await fetch(`${aiServiceUrl}/documents/${endpoint}`, {
        method: "POST",
        headers: {
            "X-Internal-Api-Key": process.env.AI_SERVICE_INTERNAL_API_KEY || "change-me"
        },
        body: formData,
        signal: AbortSignal.timeout(300_000)
    });

    let result;
    try {
        result = await response.json();
    } catch {
        throw new Error("The AI service returned an invalid response");
    }

    if (!response.ok) {
        const message = result.error?.message || result.detail || result.message;
        const error = new Error(
            typeof message === "string" ? message : "The AI service could not process this document"
        );
        error.statusCode = response.status;
        throw error;
    }

    return result;
};

export const deleteAiDocumentIndex = async (ownerId, documentId) => {
    const response = await fetch(
        `${aiServiceUrl}/documents/index/${encodeURIComponent(ownerId)}/${encodeURIComponent(documentId)}`,
        {
            method: "DELETE",
            headers: {
                "X-Internal-Api-Key": process.env.AI_SERVICE_INTERNAL_API_KEY || "change-me"
            },
            signal: AbortSignal.timeout(30_000)
        }
    );

    let result;
    try {
        result = await response.json();
    } catch {
        throw new Error("The AI service returned an invalid response");
    }

    if (!response.ok) {
        const message = result.error?.message || result.detail || result.message;
        const error = new Error(
            typeof message === "string" ? message : "Unable to delete the document search index"
        );
        error.statusCode = response.status;
        throw error;
    }

    return result;
};
