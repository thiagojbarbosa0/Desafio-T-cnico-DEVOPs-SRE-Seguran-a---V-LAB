import { useEffect, useRef, useState } from 'react';
import { List, ListItem, ListItemText, Typography } from '@mui/material';
import { onAuthStateChanged } from 'firebase/auth';
import { auth } from '../../firebaseClient';
import { SessionGate } from '../../sessionGate';
import { toast } from 'react-toastify';

export default function UserChats() {
  const [chats, setChats] = useState<Chat[]>([]);
  const [loading, setLoading] = useState(true);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const gate = useRef(new SessionGate());

  useEffect(() => {
    let active = true;
    let pending: AbortController | null = null;
    const unsubscribe = onAuthStateChanged(auth, async (user) => {
      pending?.abort();
      const uid = user?.uid ?? null;
      const generation = gate.current.begin(uid);
      // Clear previous account's data synchronously on EVERY auth transition.
      setChats([]);
      setIsLoggedIn(Boolean(user));
      setLoading(Boolean(user));
      if (!user) return;

      const controller = new AbortController();
      pending = controller;
      const valid = () => active && !controller.signal.aborted &&
        gate.current.isCurrent(uid, generation) && auth.currentUser?.uid === uid;
      try {
        const idToken = await user.getIdToken();
        if (!valid()) return;
        const response = await fetch(`${import.meta.env.VITE_API_BASE_URL || ''}/chats`, {
          method: 'GET',
          headers: { Authorization: `Bearer ${idToken}` },
          signal: controller.signal,
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        if (valid()) setChats(Array.isArray(data.chats) ? data.chats : []);
      } catch {
        if (valid()) toast.error('Não foi possível carregar as conversas.');
      } finally {
        if (valid()) setLoading(false);
      }
    });
    return () => { active = false; pending?.abort(); gate.current.begin(null); unsubscribe(); };
  }, []);

  return (
    <>
      <Typography variant="h6" sx={{ textAlign: 'center', margin: '1em 0' }}>Conversas anteriores</Typography>
      {loading ? (
        <Typography variant="body2" sx={{ padding: '1em', textAlign: 'center', color: '#888' }}>Carregando...</Typography>
      ) : !isLoggedIn ? (
        <Typography variant="body2" sx={{ padding: '1em', textAlign: 'center', color: '#888' }}>Entre para visualizar suas conversas.</Typography>
      ) : chats.length === 0 ? (
        <Typography variant="body2" sx={{ padding: '1em', textAlign: 'center', color: '#888' }}>Você não tem conversas salvas.</Typography>
      ) : (
        <List sx={{ backgroundColor: '#f5f6f8', fontSize: '0.9em' }}>
          {chats.map((chat, index) => (
            <ListItem key={index}>
              <ListItemText primary={chat.title} secondary={chat.timestamp} />
            </ListItem>
          ))}
        </List>
      )}
    </>
  );
}
