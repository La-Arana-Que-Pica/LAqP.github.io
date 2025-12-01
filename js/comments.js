/* LAqP — Comments Widget (Firebase Auth + Firestore)
   Requisitos:
   - Cargar SDKs compat en la página:
     https://www.gstatic.com/firebasejs/10.12.3/firebase-app-compat.js
     https://www.gstatic.com/firebasejs/10.12.3/firebase-auth-compat.js
     https://www.gstatic.com/firebasejs/10.12.3/firebase-firestore-compat.js
   - Llamar CommentsWidget.init({ containerId, pageId, firebaseConfig })
*/

window.CommentsWidget = (function(){
  const state = {
    app: null,
    auth: null,
    db: null,
    user: null,
    unsub: null,
    pageId: null,
    els: {}
  };

  function el(tag, attrs={}, children=[]){
    const n = document.createElement(tag);
    for(const [k,v] of Object.entries(attrs)){
      if(k === 'class') n.className = v;
      else if(k === 'text') n.textContent = v;
      else if(k.startsWith('on') && typeof v === 'function') n.addEventListener(k.slice(2), v);
      else n.setAttribute(k, v);
    }
    if(!Array.isArray(children)) children = [children];
    for(const c of children){
      if(c == null) continue;
      if(typeof c === 'string') n.appendChild(document.createTextNode(c));
      else n.appendChild(c);
    }
    return n;
  }

  function fmtDate(ts){
    try{
      const d = ts?.toDate ? ts.toDate() : (ts instanceof Date ? ts : new Date(ts));
      return d.toLocaleString();
    } catch(_){ return ''; }
  }

  function sanitizeKey(s){
    return String(s || location.pathname).replace(/[^\w\-/.]/g,'_').slice(0, 180);
  }

  function renderShell(container){
    const header = el('div', { class: 'cw-header' }, [
      el('div', { class: 'cw-user' }, [
        el('img', { class: 'cw-avatar', alt: 'Avatar', src: '', style: 'display:none' }),
        el('span', { class: 'cw-username', text: '' })
      ]),
      el('div', { class: 'cw-actions' }, [
        el('button', { class: 'cw-btn cw-btn-google', id: 'cw-signin', text: 'Iniciar sesión con Google' }),
        el('button', { class: 'cw-btn cw-btn-secondary', id: 'cw-signout', text: 'Salir', style: 'display:none' })
      ])
    ]);

    const form = el('div', { class: 'cw-form' }, [
      el('textarea', { class: 'cw-input', id: 'cw-text', rows: '3', placeholder: 'Escribí tu comentario (hasta 1000 caracteres)' }),
      el('button', { class: 'cw-btn cw-btn-primary', id: 'cw-post', text: 'Publicar', disabled: true })
    ]);

    const list = el('div', { class: 'cw-list', id: 'cw-list' });

    container.innerHTML = '';
    container.appendChild(header);
    container.appendChild(form);
    container.appendChild(list);

    state.els = {
      header, form, list,
      signinBtn: header.querySelector('#cw-signin'),
      signoutBtn: header.querySelector('#cw-signout'),
      avatar: header.querySelector('.cw-avatar'),
      username: header.querySelector('.cw-username'),
      text: form.querySelector('#cw-text'),
      postBtn: form.querySelector('#cw-post'),
    };

    state.els.signinBtn.addEventListener('click', signIn);
    state.els.signoutBtn.addEventListener('click', signOut);
    state.els.text.addEventListener('input', onInputChanged);
    state.els.postBtn.addEventListener('click', postComment);
  }

  function onInputChanged(){
    const v = state.els.text.value.trim();
    const lenOk = v.length > 0 && v.length <= 1000;
    state.els.postBtn.disabled = !(state.user && lenOk);
  }

  async function signIn(){
    try{
      const provider = new firebase.auth.GoogleAuthProvider();
      await state.auth.signInWithPopup(provider);
    } catch(e){
      console.error('Sign-in error', e);
      alert('No se pudo iniciar sesión. Intentá nuevamente.');
    }
  }

  async function signOut(){
    try{
      await state.auth.signOut();
    } catch(e){
      console.error('Sign-out error', e);
    }
  }

  async function postComment(){
    const txt = state.els.text.value.trim();
    if(!state.user || txt.length === 0 || txt.length > 1000) return;

    state.els.postBtn.disabled = true;
    state.els.postBtn.textContent = 'Publicando...';

    try{
      const col = state.db.collection('pages').doc(state.pageId).collection('comments');
      await col.add({
        text: txt,
        userId: state.user.uid,
        userName: state.user.displayName || 'Usuario',
        userPhoto: state.user.photoURL || '',
        createdAt: firebase.firestore.FieldValue.serverTimestamp(),
        updatedAt: firebase.firestore.FieldValue.serverTimestamp(),
      });
      state.els.text.value = '';
      onInputChanged();
    } catch(e){
      console.error('Post error', e);
      alert('No se pudo publicar el comentario.');
    } finally {
      state.els.postBtn.textContent = 'Publicar';
      onInputChanged();
    }
  }

  function renderCommentItem(doc){
    const data = doc.data() || {};
    const isOwner = state.user && state.user.uid === data.userId;

    const avatar = el('img', { class: 'cw-item-avatar', alt: '', src: data.userPhoto || '' });
    if(!data.userPhoto) avatar.style.display = 'none';

    const name = el('span', { class: 'cw-item-name', text: data.userName || 'Usuario' });
    const date = el('span', { class: 'cw-item-date', text: fmtDate(data.createdAt) });

    const text = el('div', { class: 'cw-item-text' });
    text.textContent = data.text || ''; // evitar XSS

    const actions = el('div', { class: 'cw-item-actions' });
    if(isOwner){
      const delBtn = el('button', { class: 'cw-link', text: 'Eliminar' });
      delBtn.addEventListener('click', async ()=>{
        if(!confirm('¿Eliminar este comentario?')) return;
        try{
          await doc.ref.delete();
        }catch(e){
          console.error('Delete error', e);
          alert('No se pudo eliminar.');
        }
      });
      actions.appendChild(delBtn);
    }

    const header = el('div', { class: 'cw-item-header' }, [
      name, el('span', { text: ' • ' }), date
    ]);

    const content = el('div', { class: 'cw-item-content' }, [header, text, actions]);

    const item = el('div', { class: 'cw-item' }, [
      avatar, content
    ]);
    return item;
  }

  function subscribe(){
    if(state.unsub) { state.unsub(); state.unsub = null; }
    const col = state.db.collection('pages').doc(state.pageId).collection('comments')
                  .orderBy('createdAt', 'desc');
    state.unsub = col.onSnapshot(snap=>{
      state.els.list.innerHTML = '';
      if(snap.empty){
        state.els.list.appendChild(el('div', { class: 'cw-empty', text: 'Sé el primero en comentar.' }));
        return;
      }
      snap.forEach(doc=>{
        state.els.list.appendChild(renderCommentItem(doc));
      });
    }, err=>{
      console.error('Snapshot error', err);
      state.els.list.innerHTML = '<div class="cw-empty">No se pudieron cargar los comentarios.</div>';
    });
  }

  function updateUIUser(user){
    state.user = user || null;
    if(state.user){
      state.els.signinBtn.style.display = 'none';
      state.els.signoutBtn.style.display = '';
      state.els.username.textContent = state.user.displayName || '';
      if(state.user.photoURL){
        state.els.avatar.src = state.user.photoURL;
        state.els.avatar.style.display = '';
      } else {
        state.els.avatar.style.display = 'none';
      }
    } else {
      state.els.signinBtn.style.display = '';
      state.els.signoutBtn.style.display = 'none';
      state.els.username.textContent = '';
      state.els.avatar.style.display = 'none';
    }
    onInputChanged();
  }

  function ensureFirebase(config){
    if(!window.firebase || !firebase.initializeApp){
      throw new Error('Firebase SDK no cargado. Incluí los scripts compat de app, auth y firestore.');
    }
    // evitar doble init si ya existe
    try {
      state.app = firebase.app();
    } catch(_){
      state.app = firebase.initializeApp(config);
    }
    state.auth = firebase.auth();
    state.db = firebase.firestore();
  }

  function init({ containerId='comments', pageId, firebaseConfig }){
    const container = document.getElementById(containerId);
    if(!container){
      console.error('CommentsWidget: no se encontró container', containerId);
      return;
    }
    if(!firebaseConfig || !firebaseConfig.apiKey){
      container.innerHTML = '<div class="cw-empty">Falta configurar Firebase (apiKey).</div>';
      return;
    }

    state.pageId = sanitizeKey(pageId || location.pathname);
    ensureFirebase(firebaseConfig);
    renderShell(container);

    // Auth state
    state.auth.onAuthStateChanged(user=>{
      updateUIUser(user);
    });

    // Suscripción a Firestore
    subscribe();
  }

  return { init };
})();