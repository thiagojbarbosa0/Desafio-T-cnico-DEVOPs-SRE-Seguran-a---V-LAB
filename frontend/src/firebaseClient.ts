import { getApps, initializeApp } from 'firebase/app';
import { getAuth, connectAuthEmulator } from 'firebase/auth';
import { getDatabase, connectDatabaseEmulator } from 'firebase/database';
import firebaseConfig from './firebaseConfig';

export const app = getApps().length ? getApps()[0] : initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const database = getDatabase(app);

if (import.meta.env.VITE_USE_FIREBASE_EMULATORS === 'true') {
  // Must be configured BEFORE any authentication/database operations.
  connectAuthEmulator(auth, 'http://127.0.0.1:9099', { disableWarnings: true });
  connectDatabaseEmulator(database, '127.0.0.1', 9000);
}
