import React, { useState, useEffect } from 'react';

// Componente principal de la aplicación EDÉN
export default function App() {
  // Estado para almacenar el token JWT
  const [token, setToken] = useState(localStorage.getItem('token') || '');
  // Estado para controlar si el usuario está autenticado
  const [authenticated, setAuthenticated] = useState(false);
  // Estado para almacenar datos del usuario autenticado
  const [user, setUser] = useState(null);
  // Estado para controlar carga y errores
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Función para actualizar token y estado de autenticación
  function handleLoginSuccess(newToken) {
    localStorage.setItem('token', newToken);
    setToken(newToken);
    setAuthenticated(true);
    setError('');
  }

  // Función para cerrar sesión
  function logout() {
    localStorage.removeItem('token');
    setToken('');
    setAuthenticated(false);
    setUser(null);
    setError('');
  }

  // Función para llamar a la API con token en Authorization
  async function apiFetch(path, options = {}) {
    const headers = options.headers ? {...options.headers} : {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    try {
      const res = await fetch(`/api${path}`, {...options, headers});
      if (res.status === 401) {
        // Token inválido o expirado
        logout();
        throw new Error('Sesión expirada. Por favor, inicie sesión de nuevo.');
      }
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || 'Error en la comunicación con el servidor.');
      }
      return await res.json();
    } catch (err) {
      throw err;
    }
  }

  // Efecto para validar token y obtener datos del usuario al montar o cambiar token
  useEffect(() => {
    if (!token) {
      setAuthenticated(false);
      setUser(null);
      return;
    }
    setLoading(true);
    apiFetch('/auth/me')
      .then(data => {
        setUser(data);
        setAuthenticated(true);
        setError('');
      })
      .catch(() => {
        logout();
      })
      .finally(() => setLoading(false));
  }, [token]);

  // Componente formulario de login y registro
  function AuthForm() {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [mode, setMode] = useState('login'); // 'login' o 'register'
    const [formError, setFormError] = useState('');
    const [submitting, setSubmitting] = useState(false);

    async function handleSubmit(e) {
      e.preventDefault();
      setFormError('');
      if (!username.trim() || !password.trim()) {
        setFormError('Por favor, complete todos los campos.');
        return;
      }
      setSubmitting(true);
      try {
        const params = new URLSearchParams();
        params.append('username', username.trim());
        params.append('password', password);
        const res = await fetch(`/api/auth/${mode}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: params.toString(),
        });
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data.detail || 'Error en la autenticación.');
        }
        const data = await res.json();
        if (data.access_token) {
          handleLoginSuccess(data.access_token);
          setUsername('');
          setPassword('');
        } else {
          throw new Error('No se recibió token de acceso.');
        }
      } catch (err) {
        setFormError(err.message);
      } finally {
        setSubmitting(false);
      }
    }

    return (
      <div className="auth-container">
        <h2>{mode === 'login' ? 'Iniciar Sesión' : 'Registrar Cuenta'}</h2>
        <form onSubmit={handleSubmit} className="auth-form" autoComplete="off">
          <label htmlFor="username">Usuario</label>
          <input
            id="username"
            type="text"
            value={username}
            onChange={e => setUsername(e.target.value)}
            disabled={submitting}
            autoComplete="username"
            required
          />
          <label htmlFor="password">Contraseña</label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            disabled={submitting}
            autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
            required
          />
          {formError && <p className="error">{formError}</p>}
          <button type="submit" disabled={submitting}>
            {submitting ? (mode === 'login' ? 'Ingresando...' : 'Registrando...') : (mode === 'login' ? 'Ingresar' : 'Registrar')}
          </button>
        </form>
        <p className="toggle-mode">
          {mode === 'login' ? (
            <>
              ¿No tienes cuenta?{' '}
              <button type="button" onClick={() => { setMode('register'); setFormError(''); }}>
                Regístrate aquí
              </button>
            </>
          ) : (
            <>
              ¿Ya tienes cuenta?{' '}
              <button type="button" onClick={() => { setMode('login'); setFormError(''); }}>
                Inicia sesión aquí
              </button>
            </>
          )}
        </p>
      </div>
    );
  }

  // Componente principal de la aplicación protegida
  function Dashboard() {
    const [loadingData, setLoadingData] = useState(false);
    const [projects, setProjects] = useState([]);
    const [fetchError, setFetchError] = useState('');

    // Ejemplo de carga de datos protegidos (proyectos)
    useEffect(() => {
      setLoadingData(true);
      apiFetch('/projects')
        .then(data => {
          setProjects(data);
          setFetchError('');
        })
        .catch(() => {
          // Datos de ejemplo como respaldo
          setProjects([
            { id: 1, name: 'Proyecto Ejemplo 1', status: 'En progreso' },
            { id: 2, name: 'Proyecto Ejemplo 2', status: 'Pendiente' },
          ]);
          setFetchError('No se pudo cargar datos reales, mostrando ejemplos.');
        })
        .finally(() => setLoadingData(false));
    }, []);

    return (
      <div className="dashboard">
        <header className="dashboard-header">
          <h1>Bienvenido, {user?.username || 'Usuario'}</h1>
          <button onClick={logout} className="logout-button" title="Cerrar sesión">Cerrar sesión</button>
        </header>
        <section className="dashboard-content">
          <h2>Proyectos</h2>
          {loadingData && <p>Cargando proyectos...</p>}
          {fetchError && <p className="error">{fetchError}</p>}
          {!loadingData && projects.length === 0 && <p>No hay proyectos disponibles.</p>}
          <ul className="projects-list">
            {projects.map(proj => (
              <li key={proj.id} className="project-item">
                <strong>{proj.name}</strong> — <em>{proj.status}</em>
              </li>
            ))}
          </ul>
        </section>
      </div>
    );
  }

  // Renderizado condicional según estado de autenticación y carga
  if (loading) {
    return (
      <main className="app-loading">
        <p>Cargando sesión...</p>
      </main>
    );
  }

  if (!authenticated) {
    return (
      <main className="app-auth">
        <AuthForm />
      </main>
    );
  }

  return (
    <main className="app-dashboard">
      <Dashboard />
    </main>
  );
}