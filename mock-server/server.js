const express = require('express');
const bodyParser = require('body-parser');
const cors = require('cors');
const morgan = require('morgan');
const jwt = require('jsonwebtoken');
const fs = require('fs');
const path = require('path');
const jalaali = require('jalaali-js');

const app = express();
const PORT = 4010;
const SECRET_KEY = 'mock-secret-key';
const STATIC_API_KEY = process.env.STATIC_API_KEY || 'your-secure-static-api-key';

// Middleware
app.use(cors());
app.use(bodyParser.json());
app.use(morgan('dev'));

// Load seed data into in-memory store
let db = JSON.parse(fs.readFileSync(path.join(__dirname, 'seed-data.json'), 'utf8'));

// Helper: Standardized Response Wrapper
const wrapResponse = (data, pagination = null) => {
  const response = {
    data: data,
    messagesList: [],
  };

  if (pagination) {
    response.pagination = pagination;
  }

  return response;
};

// Helper: Jalali Date Simulation
const toJalali = (isoDate) => {
  if (!isoDate) return null;
  const date = new Date(isoDate);
  const j = jalaali.toJalaali(date.getFullYear(), date.getMonth() + 1, date.getDate());

  const pad = (num) => String(num).padStart(2, '0');

  return `${j.jy}/${pad(j.jm)}/${pad(j.jd)} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
};

// Helper: Pagination Slicing
const paginate = (req, results) => {
    const page = parseInt(req.query.page) || 1;
    const pageSize = parseInt(req.query.page_size) || 10;
    const startIndex = (page - 1) * pageSize;
    const endIndex = page * pageSize;

    const paginatedResults = results.slice(startIndex, endIndex);
    const totalCount = results.length;
    const totalPage = Math.ceil(totalCount / pageSize);

    return {
        data: paginatedResults,
        pagination: {
            pageNo: page,
            pageSize: pageSize,
            totalPage: totalPage,
            totalCount: totalCount,
            lastId: null
        }
    };
};

// Auth middleware simulation
const authenticate = (req, res, next) => {
  // Check for Static API Key first
  const apiKey = req.headers['x-api-key'];
  if (apiKey) {
    if (apiKey === STATIC_API_KEY) {
      const testUsername = req.headers['x-test-user'];
      if (testUsername) {
        const user = db.users.find(u => u.username === testUsername);
        if (!user) return res.status(401).json({ detail: `Test user ${testUsername} not found` });
        req.user = user;
      } else {
        // Fallback to first superuser
        const superuser = db.users.find(u => u.is_superuser || u.is_staff);
        if (superuser) req.user = superuser;
      }
      return next();
    } else {
      return res.status(403).json({ detail: 'Invalid API Key' });
    }
  }

  // Check for JWT token
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1];

  if (!token) return next();

  try {
    const decoded = jwt.verify(token, SECRET_KEY);
    req.user = db.users.find(u => u.id === decoded.id);
    next();
  } catch (err) {
    return res.status(403).json({ detail: 'Invalid token' });
  }
};

app.use(authenticate);

// Generic CRUD Handlers
const createCrudHandlers = (resourceName, dbKey, lookupField = 'id') => {
    // List
    app.get(`/api/${resourceName}/`, (req, res) => {
        const paginated = paginate(req, db[dbKey]);
        res.json(wrapResponse(paginated.data, paginated.pagination));
    });

    // Retrieve
    app.get(`/api/${resourceName}/:lookup/`, (req, res) => {
        const item = db[dbKey].find(i => String(i[lookupField]) === req.params.lookup);
        if (!item) return res.status(404).json({ detail: 'Not found.' });
        res.json(wrapResponse(item));
    });

    // Create
    app.post(`/api/${resourceName}/`, (req, res) => {
        const newItem = {
            id: db[dbKey].length > 0 ? Math.max(...db[dbKey].map(i => i.id)) + 1 : 1,
            ...req.body,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString()
        };
        db[dbKey].push(newItem);
        res.status(201).json(wrapResponse(newItem));
    });

    // Update (PUT)
    app.put(`/api/${resourceName}/:lookup/`, (req, res) => {
        const index = db[dbKey].findIndex(i => String(i[lookupField]) === req.params.lookup);
        if (index === -1) return res.status(404).json({ detail: 'Not found.' });
        db[dbKey][index] = { ...db[dbKey][index], ...req.body, updated_at: new Date().toISOString() };
        res.json(wrapResponse(db[dbKey][index]));
    });

    // Partial Update (PATCH)
    app.patch(`/api/${resourceName}/:lookup/`, (req, res) => {
        const index = db[dbKey].findIndex(i => String(i[lookupField]) === req.params.lookup);
        if (index === -1) return res.status(404).json({ detail: 'Not found.' });
        db[dbKey][index] = { ...db[dbKey][index], ...req.body, updated_at: new Date().toISOString() };
        res.json(wrapResponse(db[dbKey][index]));
    });

    // Destroy
    app.delete(`/api/${resourceName}/:lookup/`, (req, res) => {
        const index = db[dbKey].findIndex(i => String(i[lookupField]) === req.params.lookup);
        if (index === -1) return res.status(404).json({ detail: 'Not found.' });
        db[dbKey].splice(index, 1);
        res.status(204).send();
    });
};

// --- Custom Overrides & Enriched Routes ---

// Auth
app.post('/api/token/', (req, res) => {
  const { username, password } = req.body;
  const user = db.users.find(u => u.username === username);
  if (user) {
    const accessToken = jwt.sign({ id: user.id, username: user.username }, SECRET_KEY, { expiresIn: '1h' });
    const refreshToken = jwt.sign({ id: user.id, username: user.username }, SECRET_KEY, { expiresIn: '1d' });
    res.json(wrapResponse({ access: accessToken, refresh: refreshToken }));
  } else {
    res.status(401).json({ detail: 'No active account found with the given credentials' });
  }
});

app.post('/api/token/refresh/', (req, res) => {
  const { refresh } = req.body;
  if (!refresh) return res.status(400).json({ detail: 'Refresh token required' });
  try {
    const decoded = jwt.verify(refresh, SECRET_KEY);
    const accessToken = jwt.sign({ id: decoded.id, username: decoded.username }, SECRET_KEY, { expiresIn: '1h' });
    res.json(wrapResponse({ access: accessToken }));
  } catch (err) {
    res.status(401).json({ detail: 'Token is invalid or expired' });
  }
});

app.post('/api/auth/admin-login/', (req, res) => {
    const { username, password } = req.body;
    const user = db.users.find(u => u.username === username && u.is_staff);
    if (user) {
      const accessToken = jwt.sign({ id: user.id, username: user.username }, SECRET_KEY, { expiresIn: '1h' });
      const refreshToken = jwt.sign({ id: user.id, username: user.username }, SECRET_KEY, { expiresIn: '1d' });
      res.json(wrapResponse({ access: accessToken, refresh: refreshToken }));
    } else {
      res.status(401).json({ detail: 'No active account found with the given credentials' });
    }
});

app.get('/api/users/me/', (req, res) => {
    if (!req.user) return res.status(401).json({ detail: 'Authentication credentials were not provided.' });
    res.json(wrapResponse(req.user));
});

// Posts with Localization and Enrichment
const enrichPost = (post, lang) => {
    const translation = post.translations.find(t => t.language_code === lang) ||
                       post.translations.find(t => t.language_code === 'en') ||
                       post.translations[0];

    const authorProfile = db.authorProfiles.find(ap => ap.user === post.author);
    const category = db.categories.find(c => c.id === post.category);
    const cover_media = db.medias.find(m => m.id === post.cover_media);
    const tags = db.tags.filter(t => post.tags.includes(t.id));

    return {
        id: post.id,
        status: post.status,
        visibility: post.visibility,
        is_hot: post.is_hot,
        published_at: toJalali(post.published_at),
        views_count: post.views_count,
        slug: translation.slug,
        title: translation.title,
        excerpt: translation.excerpt,
        reading_time_sec: translation.reading_time_sec,
        author: authorProfile ? {
            display_name: authorProfile.display_name,
            avatar: db.medias.find(m => m.id === authorProfile.avatar)
        } : null,
        category: category ? category.name : null,
        cover_media: cover_media ? {
            url: cover_media.url,
            width: cover_media.width,
            height: cover_media.height,
            alt_text: cover_media.alt_text
        } : null,
        tags: tags,
        likes_count: db.reactions.filter(r => r.content_type === 'post' && r.object_id === post.id && r.reaction === 'like').length,
        comments_count: db.comments.filter(c => c.post === post.id && c.status === 'approved').length
    };
};

app.get('/api/posts/', (req, res) => {
    let results = [...db.posts];
    const lang = req.query.lang || 'en';

    if (req.query.category) results = results.filter(p => String(p.category) === String(req.query.category));
    if (req.query.is_hot) results = results.filter(p => p.is_hot === (req.query.is_hot === 'true'));
    if (req.query.search) {
        const q = req.query.search.toLowerCase();
        results = results.filter(p => {
            return p.translations.some(t => t.title.toLowerCase().includes(q) || t.content.toLowerCase().includes(q));
        });
    }

    const enrichedResults = results.map(post => enrichPost(post, lang));
    const paginated = paginate(req, enrichedResults);
    res.json(wrapResponse(paginated.data, paginated.pagination));
});

app.get('/api/posts/:slug/', (req, res) => {
    const lang = req.query.lang || 'en';
    const post = db.posts.find(p => p.translations.some(t => t.slug === req.params.slug));

    if (!post) return res.status(404).json({ detail: 'Not found.' });

    const enriched = enrichPost(post, lang);
    const translation = post.translations.find(t => t.language_code === lang) ||
                       post.translations.find(t => t.language_code === 'en') ||
                       post.translations[0];

    const og_image = db.medias.find(m => m.id === post.og_image);

    res.json(wrapResponse({
        ...enriched,
        content: translation.content,
        seo_title: translation.seo_title,
        seo_description: translation.seo_description,
        og_image: og_image,
        media_attachments: []
    }));
});

// Alias for retrieve by slug
app.get('/api/posts/slug/:slug/', (req, res) => {
    const lang = req.query.lang || 'en';
    const post = db.posts.find(p => p.translations.some(t => t.slug === req.params.slug));
    if (!post) return res.status(404).json({ detail: 'No post was found with this slug.' });

    const enriched = enrichPost(post, lang);
    const translation = post.translations.find(t => t.language_code === lang) ||
                       post.translations.find(t => t.language_code === 'en') ||
                       post.translations[0];

    res.json(wrapResponse({
        ...enriched,
        content: translation.content,
        seo_title: translation.seo_title,
        seo_description: translation.seo_description,
        media_attachments: []
    }));
});

app.post('/api/posts/:slug/publish/', (req, res) => {
    const postIndex = db.posts.findIndex(p => p.translations.some(t => t.slug === req.params.slug));
    if (postIndex === -1) return res.status(404).json({ detail: 'Not found.' });
    db.posts[postIndex].status = 'published';
    db.posts[postIndex].published_at = new Date().toISOString();
    res.json(wrapResponse(enrichPost(db.posts[postIndex], req.query.lang || 'en')));
});

app.get('/api/posts/:slug/similar/', (req, res) => {
    const lang = req.query.lang || 'en';
    const post = db.posts.find(p => p.translations.some(t => t.slug === req.params.slug));
    if (!post) return res.status(404).json({ detail: 'Not found.' });

    const similar = db.posts.filter(p => p.category === post.category && p.id !== post.id).slice(0, 5);
    res.json(wrapResponse(similar.map(p => enrichPost(p, lang))));
});

app.get('/api/posts/:slug/same-category/', (req, res) => {
    const lang = req.query.lang || 'en';
    const post = db.posts.find(p => p.translations.some(t => t.slug === req.params.slug));
    if (!post) return res.status(404).json({ detail: 'Not found.' });

    const sameCategory = db.posts.filter(p => p.category === post.category && p.id !== post.id);
    const paginated = paginate(req, sameCategory.map(p => enrichPost(p, lang)));
    res.json(wrapResponse(paginated.data, paginated.pagination));
});

app.get('/api/posts/:slug/related/', (req, res) => {
    const lang = req.query.lang || 'en';
    const post = db.posts.find(p => p.translations.some(t => t.slug === req.params.slug));
    if (!post) return res.status(404).json({ detail: 'Not found.' });

    const related = db.posts.filter(p => p.tags.some(t => post.tags.includes(t)) && p.id !== post.id);
    const paginated = paginate(req, related.map(p => enrichPost(p, lang)));
    res.json(wrapResponse(paginated.data, paginated.pagination));
});

// Nested Comments
app.get('/api/posts/:post_slug/comments/', (req, res) => {
    const post = db.posts.find(p => p.translations.some(t => t.slug === req.params.post_slug));
    if (!post) return res.status(404).json({ detail: 'Not found.' });
    const comments = db.comments.filter(c => c.post === post.id && c.status === 'approved');

    const enrichedComments = comments.map(c => {
        const user = db.users.find(u => u.id === c.user);
        return {
            ...c,
            user: user ? { username: user.username, profile_picture: user.profile_picture } : null,
            likes_count: db.reactions.filter(r => r.content_type === 'comment' && r.object_id === c.id && r.reaction === 'like').length
        };
    });

    const paginated = paginate(req, enrichedComments);
    res.json(wrapResponse(paginated.data, paginated.pagination));
});

// Initialize all CRUD routes
createCrudHandlers('users', 'users');
createCrudHandlers('authors', 'authorProfiles', 'user');
createCrudHandlers('categories', 'categories');
createCrudHandlers('tags', 'tags');
createCrudHandlers('series', 'series');
createCrudHandlers('revisions', 'revisions');
createCrudHandlers('media', 'medias');
createCrudHandlers('comments', 'comments');
createCrudHandlers('reactions', 'reactions');
createCrudHandlers('pages', 'pages');
createCrudHandlers('menus', 'menus');
createCrudHandlers('menu-items', 'menuItems');

// Start server
app.listen(PORT, () => {
  console.log(`Production-grade Mock server running at http://localhost:${PORT}`);
});
