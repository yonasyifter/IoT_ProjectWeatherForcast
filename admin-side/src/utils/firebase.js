import { initializeApp } from 'firebase/app'
import { getAuth } from 'firebase/auth'
import { getFirestore } from 'firebase/firestore'

const firebaseConfig = {
  apiKey: 'AIzaSyCvG8Y4Uet93K-ER4NqCqgpuGm5y0fu1vM',
  authDomain: 'iot-project-49099.firebaseapp.com',
  databaseURL: 'https://iot-project-49099-default-rtdb.europe-west1.firebasedatabase.app',
  projectId: 'iot-project-49099',
  storageBucket: 'iot-project-49099.firebasestorage.app',
  messagingSenderId: '526438270092',
  appId: '1:526438270092:web:712e4cd90b387824e6a7a9',
  measurementId: 'G-N7VTGZ5SJL',
}

const app = initializeApp(firebaseConfig)
export const auth = getAuth(app)
export const db = getFirestore(app)
