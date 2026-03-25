// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";

// Your web app's Firebase configuration
const firebaseConfig = {
  apiKey: "AIzaSyAcjGtT22A8N48fzIoBT7eJCP3yAR5YmsQ",
  authDomain: "competesmart-f0b5c.firebaseapp.com",
  projectId: "competesmart-f0b5c",
  storageBucket: "competesmart-f0b5c.firebasestorage.app",
  messagingSenderId: "291421818766",
  appId: "1:291421818766:web:07bd3ad26ad570645a9edf"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
// Initialize Firebase Auth and get a reference to the service
export const auth = getAuth(app);