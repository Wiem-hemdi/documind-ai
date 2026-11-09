import DocumentChatMessage from "../models/DocumentChatMessage.js";

export const listDocumentChatHistory = async (userId, documentId) => {
    return DocumentChatMessage.find({ owner: userId, document: documentId })
        .select("role content createdAt")
        .sort({ createdAt: 1, _id: 1 })
        .lean();
};

export const getRecentDocumentChatHistory = async (userId, documentId, limit = 12) => {
    const messages = await DocumentChatMessage.find({ owner: userId, document: documentId })
        .select("role content")
        .sort({ createdAt: -1, _id: -1 })
        .limit(limit)
        .lean();

    return messages.reverse().map(({ role, content }) => ({ role, content }));
};

export const saveDocumentChatExchange = async (
    userId,
    documentId,
    question,
    answer
) => {
    const timestamp = new Date();
    await DocumentChatMessage.insertMany([
        {
            owner: userId,
            document: documentId,
            role: "user",
            content: question,
            createdAt: timestamp
        },
        {
            owner: userId,
            document: documentId,
            role: "assistant",
            content: answer,
            createdAt: new Date(timestamp.getTime() + 1)
        }
    ]);
};

export const clearDocumentChatHistory = async (userId, documentId) => {
    return DocumentChatMessage.deleteMany({ owner: userId, document: documentId });
};
