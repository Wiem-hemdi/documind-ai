import { mkdirSync } from "node:fs";
import path from "node:path";
import { randomUUID } from "node:crypto";
import express from "express";
import multer from "multer";
import { protect } from "../middlewares/auth.middleware.js";
import {
    askAboutDocument,
    getDocumentChatHistory,
    getDocumentContent,
    getDocumentFile,
    removeDocument,
    removeDocumentChatHistory,
    listDocuments,
    uploadDocument
} from "../controllers/document.controller.js";

const uploadDirectory = path.resolve(
    process.env.UPLOAD_DIR || path.join(process.cwd(), "uploads")
);
const maxFileSize = 20 * 1024 * 1024;
const allowedExtensions = new Set([
    ".pdf", ".docx", ".txt", ".md", ".csv", ".xlsx", ".pptx"
]);

mkdirSync(uploadDirectory, { recursive: true });

const storage = multer.diskStorage({
    destination: (_req, _file, callback) => callback(null, uploadDirectory),
    filename: (_req, file, callback) => {
        const extension = path.extname(file.originalname).toLowerCase();
        callback(null, `${randomUUID()}${extension}`);
    }
});

const uploader = multer({
    storage,
    limits: { fileSize: maxFileSize, files: 1 },
    fileFilter: (_req, file, callback) => {
        const extension = path.extname(file.originalname).toLowerCase();
        if (!allowedExtensions.has(extension)) {
            callback(new Error("Unsupported document type"));
            return;
        }
        callback(null, true);
    }
});

const uploadSingleDocument = (req, res, next) => {
    uploader.single("file")(req, res, (error) => {
        if (!error) {
            next();
            return;
        }

        const statusCode = error instanceof multer.MulterError ? 400 : 415;
        const message = error.code === "LIMIT_FILE_SIZE"
            ? "The maximum file size is 20 MB"
            : error.code === "LIMIT_UNEXPECTED_FILE"
                ? "Upload one document at a time"
                : error.message;

        res.status(statusCode).json({ success: false, message });
    });
};

const router = express.Router();

router.get("/", protect, listDocuments);
router.post("/", protect, uploadSingleDocument, uploadDocument);
router.get("/:documentId/file", protect, getDocumentFile);
router.get("/:documentId/history", protect, getDocumentChatHistory);
router.delete("/:documentId/history", protect, removeDocumentChatHistory);
router.get("/:documentId/content", protect, getDocumentContent);
router.post("/:documentId/chat", protect, askAboutDocument);
router.delete("/:documentId", protect, removeDocument);

export default router;
