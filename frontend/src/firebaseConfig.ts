// No connection to the upstream application's Firebase project by default.
// Use local emulators, or specify YOUR OWN authorized Firebase project in .env.local.
const local = import.meta.env.VITE_USE_FIREBASE_EMULATORS === 'true';
const id = local ? 'demo-coursesphere-vlab' : import.meta.env.VITE_FIREBASE_PROJECT_ID;
const firebaseConfig = {
  apiKey: local ? 'demo-api-key' : import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: `${id}.firebaseapp.com`,
  databaseURL: `https://${id}${local ? "-default-rtdb" : ""}.firebaseio.com`,
  projectId: id,
  storageBucket: `${id}.appspot.com`,
  messagingSenderId: local ? '000000000000' : import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: local ? '1:000000000000:web:demo' : import.meta.env.VITE_FIREBASE_APP_ID,
};
if (!local && (!id || !firebaseConfig.apiKey || !firebaseConfig.appId)) {
  throw new Error('Set VITE_USE_FIREBASE_EMULATORS=true or configure an authorized Firebase project.');
}
export default firebaseConfig;
