import Document from "../models/Document.js";

export const listUserDocuments = async (userId) => {
    return Document.find({ owner: userId })
        .select("originalName extension mimeType size status createdAt")
        .sort({ createdAt: -1 })
        .lean();
};

export const saveUserDocument = async (userId, file) => {
    const document = await Document.create({
        owner: userId,
        originalName: file.originalname,
        storedName: file.filename,
        extension: file.extension,
        mimeType: file.mimetype || "application/octet-stream",
        size: file.size
    });

    return {
        id: document._id,
        originalName: document.originalName,
        extension: document.extension,
        mimeType: document.mimeType,
        size: document.size,
        status: document.status,
        createdAt: document.createdAt
    };
};

export const findUserDocument = async (userId, documentId) => {
    return Document.findOne({ _id: documentId, owner: userId });
};

export const deleteUserDocument = async (userId, documentId) => {
    return Document.findOneAndDelete({ _id: documentId, owner: userId });
};