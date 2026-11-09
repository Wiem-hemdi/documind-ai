import { readFile, unlink } from "node:fs/promises";
import path from "node:path";
import mongoose from "mongoose";
import {
    deleteUserDocument,
    findUserDocument,
    listUserDocuments,
    saveUserDocument
} from "../services/document.service.js";
import { deleteAiDocumentIndex, requestAiDocument } from "../services/ai.service.js";
import {
    clearDocumentChatHistory,
    getRecentDocumentChatHistory,
    listDocumentChatHistory,
    saveDocumentChatExchange
} from "../services/document-chat.service.js";

const findOwnedDocument = async (userId, documentId) => {
    if (!mongoose.Types.ObjectId.isValid(documentId)) return null;
    return findUserDocument(userId, documentId);
};

const inlineContentTypes = {
    ".pdf": "application/pdf",
    ".txt": "text/plain; charset=utf-8",
    ".md": "text/plain; charset=utf-8",
    ".csv": "text/csv; charset=utf-8",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg"
};

const encodeFilename = (filename) => encodeURIComponent(filename)
    .replace(/['()*]/g, (character) => `%${character.charCodeAt(0).toString(16).toUpperCase()}`);

export const listDocuments = async (req, res) => {
    try {
        const documents = await listUserDocuments(req.user.id);
        return res.status(200).json({ success: true, data: documents });
    } catch (error) {
        console.error("Document list failed:", error.message);
        return res.status(500).json({
            success: false,
            message: "Unable to load documents"
        });
    }
};

export const getDocumentFile = async (req, res) => {
    try {
        const document = await findOwnedDocument(req.user.id, req.params.documentId);
        if (!document) {
            return res.status(404).json({ success: false, message: "Document not found" });
        }

        const uploadDirectory = path.resolve(
            process.env.UPLOAD_DIR || path.join(process.cwd(), "uploads")
        );
        const storedName = path.basename(document.storedName);
        if (storedName !== document.storedName) {
            throw new Error("Invalid stored document path");
        }

        const fileBuffer = await readFile(path.join(uploadDirectory, storedName));
        const extension = path.extname(document.originalName).toLowerCase();
        const contentType = inlineContentTypes[extension] || "application/octet-stream";
        res.set({
            "Cache-Control": "private, no-store",
            "Content-Disposition": `inline; filename*=UTF-8''${encodeFilename(document.originalName)}`,
            "Content-Type": contentType,
            "X-Content-Type-Options": "nosniff"
        });
        return res.status(200).send(fileBuffer);
    } catch (error) {
        if (error.code === "ENOENT") {
            return res.status(404).json({ success: false, message: "The stored document file is missing" });
        }
        console.error("Document preview failed:", error.message);
        return res.status(500).json({
            success: false,
            message: "Unable to preview document"
        });
    }
};

export const uploadDocument = async (req, res) => {
    if (!req.file) {
        return res.status(400).json({
            success: false,
            message: "Choose a document to upload"
        });
    }

    try {
        req.file.extension = req.file.originalname
            .slice(req.file.originalname.lastIndexOf("."))
            .toLowerCase();
        const document = await saveUserDocument(req.user.id, req.file);

        return res.status(201).json({
            success: true,
            message: "Document uploaded successfully",
            data: document
        });
    } catch (error) {
        await unlink(req.file.path).catch(() => {});
        console.error("Document upload failed:", error.message);
        return res.status(500).json({
            success: false,
            message: "Unable to save document"
        });
    }
};

export const getDocumentContent = async (req, res) => {
    try {
        const document = await findOwnedDocument(req.user.id, req.params.documentId);
        if (!document) {
            return res.status(404).json({ success: false, message: "Document not found" });
        }

        const data = await requestAiDocument(document, "extract");
        return res.status(200).json({ success: true, data });
    } catch (error) {
        console.error("Document extraction failed:", error.message);
        return res.status(error.statusCode || (error.code === "ENOENT" ? 404 : 503)).json({
            success: false,
            message: error.code === "ENOENT"
                ? "The stored document file is missing"
                : error.message || "Unable to extract document content"
        });
    }
};

export const getDocumentChatHistory = async (req, res) => {
    try {
        const document = await findOwnedDocument(req.user.id, req.params.documentId);
        if (!document) {
            return res.status(404).json({ success: false, message: "Document not found" });
        }

        const history = await listDocumentChatHistory(req.user.id, document._id);
        return res.status(200).json({ success: true, data: history });
    } catch (error) {
        console.error("Document chat history load failed:", error.message);
        return res.status(500).json({
            success: false,
            message: "Unable to load document chat history"
        });
    }
};

export const askAboutDocument = async (req, res) => {
    const question = typeof req.body?.question === "string" ? req.body.question.trim() : "";
    if (!question || question.length > 2000) {
        return res.status(400).json({
            success: false,
            message: "Enter a question of at most 2,000 characters"
        });
    }

    try {
        const document = await findOwnedDocument(req.user.id, req.params.documentId);
        if (!document) {
            return res.status(404).json({ success: false, message: "Document not found" });
        }

        const history = await getRecentDocumentChatHistory(req.user.id, document._id);
        const data = await requestAiDocument(document, "chat", {
            question,
            history: JSON.stringify(history),
            owner_id: req.user.id,
            document_id: document._id.toString()
        });
        const answer = data.answer;
        await saveDocumentChatExchange(req.user.id, document._id, question, answer);
        data.history = await listDocumentChatHistory(req.user.id, document._id);
        return res.status(200).json({ success: true, data });
    } catch (error) {
        console.error("Document question failed:", error.message);
        return res.status(error.statusCode || (error.code === "ENOENT" ? 404 : 503)).json({
            success: false,
            message: error.code === "ENOENT"
                ? "The stored document file is missing"
                : error.message || "Unable to answer this question"
        });
    }
};

export const removeDocumentChatHistory = async (req, res) => {
    try {
        const document = await findOwnedDocument(req.user.id, req.params.documentId);
        if (!document) {
            return res.status(404).json({ success: false, message: "Document not found" });
        }

        await clearDocumentChatHistory(req.user.id, document._id);
        return res.status(200).json({ success: true, message: "Chat history cleared" });
    } catch (error) {
        console.error("Document chat history deletion failed:", error.message);
        return res.status(500).json({
            success: false,
            message: "Unable to clear document chat history"
        });
    }
};

export const removeDocument = async (req, res) => {
    try {
        const document = await findOwnedDocument(req.user.id, req.params.documentId);
        if (!document) {
            return res.status(404).json({ success: false, message: "Document not found" });
        }

        const uploadDirectory = path.resolve(
            process.env.UPLOAD_DIR || path.join(process.cwd(), "uploads")
        );
        const storedName = path.basename(document.storedName);
        if (storedName !== document.storedName) {
            throw new Error("Invalid stored document path");
        }

        await deleteAiDocumentIndex(req.user.id, document._id);
        try {
            await unlink(path.join(uploadDirectory, storedName));
        } catch (error) {
            if (error.code !== "ENOENT") throw error;
        }
        await deleteUserDocument(req.user.id, req.params.documentId);
        await clearDocumentChatHistory(req.user.id, req.params.documentId);
        return res.status(200).json({ success: true, message: "Document deleted" });
    } catch (error) {
        console.error("Document deletion failed:", error.message);
        return res.status(error.statusCode || 500).json({
            success: false,
            message: error.message || "Unable to delete document"
        });
    }
};