import { FormEvent, useEffect, useRef, useState } from 'react';
import { Alert, Box, Button, CircularProgress, Container, Paper, TextField, Typography } from '@mui/material';
import { fetchCourseSphereResponse, saveCourseSphereChat } from '../../api';
import { onAuthStateChanged } from 'firebase/auth';
import { auth } from '../../firebaseClient';
import { SessionGate } from '../../sessionGate';

// This is the ORIGINAL recommendation app's chat, not the separate AppSec lab.
// Messages must match the Flask validate_messages contract exactly.
type ChatLine = { sender: 'user' | 'bot'; content: string; messageID: string; timestamp: string };
const messageId = () => crypto.randomUUID().replace(/-/g, '');

export default function ChatInterface() {
  const [query, setQuery] = useState('');
  const [lines, setLines] = useState<ChatLine[]>([]);
  const [sending, setSending] = useState(false);
  const [saveError, setSaveError] = useState(false);
  const [replyError, setReplyError] = useState(false);
  const [notice, setNotice] = useState('');
  // Never reuse a hard-coded ID across distinct conversations/users.
  const chatId = useRef(`chat_${messageId()}`);
  const gate = useRef(new SessionGate());
  const [authenticated, setAuthenticated] = useState(Boolean(auth.currentUser));

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (user) => {
      gate.current.begin(user?.uid ?? null);
      // Keep no conversation, query or status from the preceding session.
      chatId.current = `chat_${messageId()}`;
      setLines([]);
      setQuery('');
      setNotice('');
      setSaveError(false);
      setReplyError(false);
      setSending(false);
      setAuthenticated(Boolean(user));
    });
    return () => { gate.current.begin(null); unsubscribe(); };
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = query.trim();
    const uid = auth.currentUser?.uid ?? null;
    if (!text || sending || !uid || !authenticated) return;
    const generation = gate.current.begin(uid);
    // The request itself is bound to the account and generation that submitted it.
    const valid = () => gate.current.isCurrent(uid, generation) && auth.currentUser?.uid === uid;
    setSending(true);
    setSaveError(false);
    setReplyError(false);
    setNotice('');
    setQuery('');
    const userMessage: ChatLine = {
      sender: 'user', content: text, messageID: messageId(), timestamp: new Date().toISOString(),
    };
    setLines((current) => valid() ? [...current, userMessage] : current);
    try {
      const { botResponse, newRecommendations } = await fetchCourseSphereResponse(text, uid);
      if (!valid()) return;
      const botMessage: ChatLine = {
        sender: 'bot', content: botResponse, messageID: messageId(), timestamp: new Date().toISOString(),
      };
      setLines((current) => valid() ? [...current, botMessage] : current);
      // Persist immediately. A failed save is NOT a failed recommendation request.
      try {
        if (!valid()) return;
        await saveCourseSphereChat(chatId.current, [userMessage, botMessage], uid);
      } catch {
        if (valid()) setSaveError(true);
      }
      if (valid() && newRecommendations.length) {
        setNotice(`${newRecommendations.length} sugestão(ões) retornada(s).`);
      }
    } catch {
      // Do not fabricate an assistant response on an API outage or invalid payload.
      if (valid()) setReplyError(true);
    } finally {
      if (valid()) setSending(false);
    }
  }

  return (
    <Container maxWidth="md" sx={{ py: 3 }}>
      <Paper variant="outlined" sx={{ borderRadius: 2, overflow: 'hidden' }}>
        <Box sx={{ p: 3, borderBottom: '1px solid', borderColor: 'divider' }}>
          <Typography variant="h5" component="h1" sx={{ fontWeight: 600 }}>CourseSphere</Typography>
          <Typography variant="body2" color="text.secondary">
            Explore disciplinas e recomendações. O mecanismo original ainda é demonstrativo.
          </Typography>
        </Box>
        <Box aria-live="polite" sx={{ p: 3, minHeight: 250, maxHeight: '55vh', overflowY: 'auto' }}>
          {lines.length === 0 && (
            <Typography color="text.secondary">Escreva uma pergunta para começar.</Typography>
          )}
          {lines.map((line) => (
            <Box key={line.messageID} sx={{ mb: 2, ml: line.sender === 'user' ? 'auto' : 0,
              maxWidth: '85%', width: 'fit-content', bgcolor: line.sender === 'user' ? '#eef3f9' : 'grey.100',
              p: 1.5, borderRadius: 1.5 }}>
              <Typography variant="caption" color="text.secondary">
                {line.sender === 'user' ? 'Você' : 'CourseSphere'}
              </Typography>
              <Typography sx={{ overflowWrap: 'anywhere' }}>{line.content}</Typography>
            </Box>
          ))}
          {sending && <CircularProgress size={20} aria-label="Processando resposta" />}
        </Box>
        {notice && <Alert severity="info">{notice}</Alert>}
        {replyError && <Alert severity="error" role="alert">
          Não foi possível consultar as recomendações. Tente novamente.
        </Alert>}
        {saveError && <Alert severity="warning" role="status">
          Não foi possível salvar esta conversa. O conteúdo permanece nesta aba.
        </Alert>}
        <Box component="form" onSubmit={handleSubmit} sx={{ p: 2, display: 'flex', alignItems: 'center', gap: 2,
          borderTop: '1px solid', borderColor: 'divider' }}>
          <TextField size="small" fullWidth label="Sua pergunta" value={query} disabled={!authenticated}
            onChange={(event) => setQuery(event.target.value)} inputProps={{ maxLength: 2000 }} />
          <Button type="submit" variant="contained" disabled={!authenticated || sending || !query.trim()}>Enviar</Button>
        </Box>
      </Paper>
    </Container>
  );
}
