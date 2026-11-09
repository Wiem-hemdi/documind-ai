import express from "express";

const router = express.Router();

router.get("/", (req, res) => {
    res.status(200).json({
        success: true,
        message: "DocuMind AI Backend is running!",
        status: "healthy"
    });
});

export default router;