import { onAuthStateChanged, createUserWithEmailAndPassword, signInWithEmailAndPassword } from "firebase/auth";
import { auth } from "./firebaseClient";
import { SessionGate } from "./sessionGate";
import { toast } from "react-toastify";

// Prefer native DOM input access over jQuery; the API file does not need a separate
// runtime or ambient declaration just to read the two authentication forms.
const inputValue = (id: string): string =>
  (document.getElementById(id) as HTMLInputElement | null)?.value ?? '';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';
const apiUrl = (route: string) => `${API_BASE}${route}`;
// Prevent late responses from being mistaken for results of another user.
const sameUser = (uid: string) => auth.currentUser?.uid === uid;



// Public signup must use Firebase Authentication's client SDK, not an unauthenticated
// backend endpoint that invokes Firebase Admin's privileged create_user function.
async function createUser(email: string, password: string) {
  const credential = await createUserWithEmailAndPassword(auth, email, password);
  return { user_id: credential.user.uid, email: credential.user.email };
}

function performSignup() {
  const email = inputValue('signup-email-input');
  const password = inputValue('signup-password-input');
  createUser(email, password)
    .then(() => { window.location.replace("/"); })
    .catch(() => toast.error("Não foi possível criar a conta. Verifique os dados e tente novamente."));
}

/**
 * This function performs the user login transaction with firebase.
 * 
 */
function performLogin() {
  const email = inputValue('login-email-input');
  const password = inputValue('login-password-input');
  signInWithEmailAndPassword(auth, email, password)
    .then(() => {
      window.location.replace("/");
    })
    .catch(() => {
      toast.error("Não foi possível entrar. Confira seus dados e tente novamente.");
    });
}



/**
 * This function sets the profile information if the user is logged in.
 * 
 * @param setMajors 
 * @param setMinors 
 * @param setYear 
 * @param setCollege 
 * @param setCourses 
 */
function setProfileInfoIfLoggedIn(
  setMajors: (value: string[]) => void,
  setMinors: (value: string[]) => void,
  setYear: (value: string) => void,
  setCollege: (value: string) => void,
  setCourses: (value: string[]) => void,
  setAbout: (value: string) => void
) {
  const gate = new SessionGate();
  let active = true;
  let pending: AbortController | null = null;
  const clearProfile = () => {
    setMajors([]); setMinors([]); setYear('');
    setCollege(''); setCourses([]); setAbout('');
  };
  const unsubscribe = onAuthStateChanged(auth, async (user) => {
    pending?.abort();
    const uid = user?.uid ?? null;
    const generation = gate.begin(uid);
    // A -> logout -> B must never retain the former user's profile fields.
    clearProfile();
    if (!user) return;
    const controller = new AbortController();
    pending = controller;
    const valid = () => active && !controller.signal.aborted &&
      gate.isCurrent(uid, generation) && auth.currentUser?.uid === uid;
    try {
      const idToken = await user.getIdToken();
      if (!valid()) return;
      const response = await fetch(apiUrl('/users/info'), {
        method: 'GET',
        headers: { Authorization: `Bearer ${idToken}` },
        signal: controller.signal,
      });
      if (!response.ok) throw new Error('Profile request failed');
      const data: unknown = await response.json();
      if (!valid()) return;
      if (data === null) return;
      if (!data || typeof data !== 'object' || Array.isArray(data))
        throw new Error('Invalid profile data');
      const profile = data as Record<string, unknown>;
      // Backend validation is authoritative; still validate types at UI boundary.
      const strings = (value: unknown): string[] =>
        Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : [];
      setMajors(strings(profile.majors));
      setMinors(strings(profile.minors));
      setCourses(strings(profile.courses));
      setYear(typeof profile.year === 'string' ? profile.year : '');
      setCollege(typeof profile.college === 'string' ? profile.college : '');
      setAbout(typeof profile.about === 'string' ? profile.about : '');
    } catch {
      if (valid()) toast.error('Não foi possível carregar o perfil.');
    }
  });
  return () => { active = false; pending?.abort(); gate.begin(null); unsubscribe(); };
}

/**
 * This function saves any profile changes that occurs on the user dashboard. 
 * 
 * @param majors 
 * @param minors 
 * @param courses 
 * @returns 
 */
async function saveProfileChanges (
  majors: string[], minors: string[], courses: string[], year: string, college: string, about: string
): Promise<boolean> {
  if (!ensureUserLoggedIn()) return false;
  const user = auth.currentUser;
  if (!user) return false;
  // Await network completion before reporting success to the user. Do not
  // include raw server errors or sensitive payloads in notification text.
  try {
    const idToken = await user.getIdToken();
    if (!sameUser(user.uid)) return false;
    const response = await fetch(apiUrl('/users/info'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${idToken}` },
      body: JSON.stringify({ majors, minors, year, college, courses, about }),
    });
    if (!response.ok || !sameUser(user.uid)) throw new Error('Profile write failed');
    toast.success('Perfil salvo com sucesso.');
    return true;
  } catch {
    toast.error('Não foi possível salvar o perfil. Tente novamente.');
    return false;
  }
}


/**
 * This functions sends the query, as well as the user id (if the user is logged in) to the backend and returns the response. 
 * 
 * @param query 
 * @returns 
 */
// Never convert API/network failures into a normal bot message. Doing so would
// silently persist outages as apparently genuine course recommendations.
type RecommendationReply = { botResponse: string; newRecommendations: unknown[] };
async function fetchCourseSphereResponse(query: string, expectedUid: string): Promise<RecommendationReply> {
  const user = auth.currentUser;
  if (!user || user.uid !== expectedUid) throw new Error('Session changed');
  const idToken = await user.getIdToken();
  if (!sameUser(user.uid)) throw new Error('Session changed');
  const response = await fetch(apiUrl('/users/query'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${idToken}` },
    body: JSON.stringify({ query }),
  });
  if (!response.ok || !sameUser(user.uid)) throw new Error('CourseSphere API request failed');
  const payload: unknown = await response.json();
  if (!sameUser(user.uid)) throw new Error('Session changed');
  if (!payload || typeof payload !== 'object') throw new Error('Invalid API response');
  const result = payload as Record<string, unknown>;
  if (typeof result.botResponse !== 'string' || !result.botResponse.trim() ||
      !Array.isArray(result.newRecommendations)) {
    throw new Error('Invalid API response');
  }
  return {
    botResponse: result.botResponse,
    newRecommendations: result.newRecommendations,
  };
}

function ensureUserLoggedIn(): boolean {
  const user = auth.currentUser;
  if (user == null) {
    alert("Not logged in");
    return false;
  }
  return true;
}


async function saveCourseSphereChat(chatId: string, messages: Message[], expectedUid: string): Promise<void> {
  const user = auth.currentUser;
  if (!user || user.uid !== expectedUid) throw new Error('Session changed');
  if (!/^chat_[a-f0-9]{32}$/.test(chatId)) throw new Error('Invalid chat ID');
  const token = await user.getIdToken();
  if (!sameUser(user.uid)) throw new Error('Session changed');
  const response = await fetch(apiUrl(`/chats/${chatId}/messages`), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify({ messages }),
  });
  if (!response.ok || !sameUser(user.uid)) throw new Error('Chat was not saved');
}


export {
  createUser,
  performSignup,
  performLogin,
  saveProfileChanges,
  setProfileInfoIfLoggedIn,
  fetchCourseSphereResponse,
  saveCourseSphereChat,
};
