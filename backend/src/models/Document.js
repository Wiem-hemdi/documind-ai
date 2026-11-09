import mongoose from "mongoose";

const documentSchema = new mongoose.Schema(
    {
        owner: {
            type: mongoose.Schema.Types.ObjectId,
            ref: "User",
            required: true,
            index: true
        },
        originalName: {
            type: String,
            required: true,
            trim: true
        },
        storedName: {
            type: String,
            required: true,
            unique: true
        },
        extension: {
            type: String,
            required: true
        },
        mimeType: {
            type: String,
            default: "application/octet-stream"
        },
        size: {
            type: Number,
            required: true
        },
        status: {
            type: String,
            enum: ["uploaded", "processing", "ready", "failed"],
            default: "uploaded"
        }
    },
    { timestamps: true }
);

const Document = mongoose.model("Document", documentSchema);

export default Document;