
import {
    registerUser,
    loginUser,
    getCurrentUser
} from "../services/auth.service.js";

// Register
export const register = async (req, res) => {
    try {
        const { firstName, lastName, email, password } = req.body;

        if (!firstName || !lastName || !email || !password) {
            return res.status(400).json({
                success: false,
                message: "All fields are required"
            });
        }

        if (password.length < 8) {
            return res.status(400).json({
                success: false,
                message: "Password must contain at least 8 characters"
            });
        }

        const result = await registerUser({
            firstName,
            lastName,
            email,
            password
        });

        return res.status(201).json({
            success: true,
            message: "Account created successfully",
            data: result
        });

    } catch (error) {
        return res.status(400).json({
            success: false,
            message: error.message
        });
    }
};

// Login
export const login = async (req, res) => {
    try {
        const { email, password } = req.body;

        if (!email || !password) {
            return res.status(400).json({
                success: false,
                message: "Email and password are required"
            });
        }

        const result = await loginUser({ email, password });

        return res.status(200).json({
            success: true,
            message: "Login successful",
            data: result
        });

    } catch (error) {
        return res.status(401).json({
            success: false,
            message: error.message
        });
    }
};

// Get current user
export const getMe = async (req, res) => {
    try {
        const user = await getCurrentUser(req.user.id);

        return res.status(200).json({
            success: true,
            data: user
        });

    } catch (error) {
        return res.status(404).json({
            success: false,
            message: error.message
        });
    }
};
