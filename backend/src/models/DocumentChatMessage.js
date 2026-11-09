import mongoose from "mongoose";

const documentChatMessageSchema = new mongoose.Schema(
    {
        owner: {
            type: mongoose.Schema.Types.ObjectId,
            ref: "User",
            required: true,
            index: true
        },
        document: {
            type: mongoose.Schema.Types.ObjectId,
            ref: "Document",
            required: true,
            index: true
        },
        role: {
            type: String,
            enum: ["user", "assistant"],
            required: true
        },
        content: {
            type: String,
            required: true,
            maxlength: 20_000
        }
    },
    { timestamps: true }
);

documentChatMessageSchema.index({ owner: 1, document: 1, createdAt: 1 });

const DocumentChatMessage = mongoose.model(
    "DocumentChatMessage",
    documentChatMessageSchema
);

export default DocumentChatMessage;
