export const DOMAINS = [
  {
    id: 'full-stack',
    title: 'Full Stack Development',
    category: 'Web Engineering',
    description: 'Master frontend, backend, databases, and DevOps with HTML, CSS, JS, React, Node.js, Express, and MongoDB.',
    coursesCount: 24,
    estimatedHours: 120,
    skills: ['React', 'Node.js', 'Express', 'MongoDB', 'JavaScript'],
    active: true,
    color: 'from-blue-500 to-indigo-600',
    iconName: 'Code2',
    popularity: '98% High Demand'
  },
  {
    id: 'machine-learning',
    title: 'Machine Learning',
    category: 'Artificial Intelligence',
    description: 'Build predictive models, neural networks, computer vision, and NLP systems with Python, PyTorch, and TensorFlow.',
    coursesCount: 18,
    estimatedHours: 140,
    skills: ['Python', 'Neural Networks', 'PyTorch', 'Scikit-Learn'],
    active: false,
    color: 'from-purple-500 to-pink-600',
    iconName: 'Cpu',
    popularity: '95% High Demand'
  },
  {
    id: 'cloud-computing',
    title: 'Cloud Computing',
    category: 'Infrastructure',
    description: 'Architect scalable cloud applications on AWS, Azure, GCP with Kubernetes, Docker, and Terraform.',
    coursesCount: 15,
    estimatedHours: 90,
    skills: ['AWS', 'Azure', 'Docker', 'Kubernetes', 'DevOps'],
    active: false,
    color: 'from-cyan-500 to-blue-600',
    iconName: 'Cloud',
    popularity: '91% High Demand'
  },
  {
    id: 'data-science',
    title: 'Data Science & Analytics',
    category: 'Big Data',
    description: 'Analyze complex data sets, create interactive visualizations, and extract insights using SQL, Pandas, and Tableau.',
    coursesCount: 16,
    estimatedHours: 110,
    skills: ['Python', 'SQL', 'Pandas', 'Tableau', 'Statistics'],
    active: false,
    color: 'from-emerald-500 to-teal-600',
    iconName: 'Database',
    popularity: '93% High Demand'
  },
  {
    id: 'cyber-security',
    title: 'Cyber Security',
    category: 'Information Security',
    description: 'Learn ethical hacking, penetration testing, network defense, cryptography, and cloud security frameworks.',
    coursesCount: 12,
    estimatedHours: 100,
    skills: ['Ethical Hacking', 'PenTesting', 'Network Security', 'Crypto'],
    active: false,
    color: 'from-rose-500 to-amber-600',
    iconName: 'ShieldCheck',
    popularity: '89% High Demand'
  }
];

export const TOPICS = [
  { id: 'html', name: 'HTML5', description: 'Semantic tags, forms, accessibility, and modern web layout structures.' },
  { id: 'css', name: 'CSS3', description: 'Flexbox, CSS Grid, animations, variables, and responsive media queries.' },
  { id: 'javascript', name: 'JavaScript (ES6+)', description: 'Promises, async/await, closures, DOM, ES modules, and array methods.' },
  { id: 'react', name: 'React.js', description: 'Hooks, state management, router, component lifecycle, and virtual DOM.' },
  { id: 'nodejs', name: 'Node.js', description: 'Event loop, file system, streams, buffer, asynchronous architecture.' },
  { id: 'express', name: 'Express.js', description: 'REST APIs, middleware routing, authentication headers, error handling.' },
  { id: 'mongodb', name: 'MongoDB', description: 'NoSQL schemas, Mongoose ORM, aggregation pipeline, indexing & security.' }
];

export const SAMPLE_QUESTIONS_20 = [
  { id: 1, topic: 'HTML', question: 'What is the purpose of the semantic <article> element in HTML5?', options: ['To define independent, self-contained content', 'To format text as italic style', 'To embed audio files', 'To create a sidebar section'], answer: 0 },
  { id: 2, topic: 'HTML', question: 'Which attribute is used to provide an alternative text for an image?', options: ['title', 'alt', 'src', 'desc'], answer: 1 },
  { id: 3, topic: 'CSS', question: 'Which CSS Flexbox property controls alignment along the cross-axis?', options: ['justify-content', 'align-items', 'flex-direction', 'flex-wrap'], answer: 1 },
  { id: 4, topic: 'CSS', question: 'What does `box-sizing: border-box` do?', options: ['Adds border around the screen', 'Includes padding and border in element total width', 'Hides element overflowing content', 'Applies shadow to borders'], answer: 1 },
  { id: 5, topic: 'JavaScript', question: 'What will `typeof NaN` evaluate to in JavaScript?', options: ['"number"', '"nan"', '"undefined"', '"object"'], answer: 0 },
  { id: 6, topic: 'JavaScript', question: 'Which method returns a new array with all elements that pass a test function?', options: ['map()', 'filter()', 'forEach()', 'reduce()'], answer: 1 },
  { id: 7, topic: 'JavaScript', question: 'What keyword creates a block-scoped variable that cannot be reassigned?', options: ['var', 'let', 'const', 'static'], answer: 2 },
  { id: 8, topic: 'React', question: 'Which Hook is used to perform side effects in functional components?', options: ['useState', 'useContext', 'useEffect', 'useMemo'], answer: 2 },
  { id: 9, topic: 'React', question: 'What is the purpose of keys when rendering lists in React?', options: ['To style list items', 'To help React identify which items changed/added/removed', 'To encrypt list data', 'To bind click handlers'], answer: 1 },
  { id: 10, topic: 'React', question: 'How do you pass data down from parent to child component?', options: ['State', 'Props', 'Redux', 'Context API'], answer: 1 },
  { id: 11, topic: 'Node.js', question: 'What module is built into Node.js to work with file paths?', options: ['fs', 'path', 'url', 'http'], answer: 1 },
  { id: 12, topic: 'Node.js', question: 'Node.js operates on what type of I/O execution model?', options: ['Multi-threaded blocking', 'Single-threaded non-blocking event loop', 'Synchronous execution', 'Parallel thread pool only'], answer: 1 },
  { id: 13, topic: 'Express.js', question: 'Which method handles HTTP POST requests in Express?', options: ['app.get()', 'app.post()', 'app.use()', 'app.request()'], answer: 1 },
  { id: 14, topic: 'Express.js', question: 'What is middleware in Express.js?', options: ['A database connection plugin', 'Functions with access to request, response, and next function', 'A CSS styling framework', 'A front-end router'], answer: 1 },
  { id: 15, topic: 'MongoDB', question: 'What form of data storage does MongoDB use internally?', options: ['Relational SQL Tables', 'BSON (Binary JSON)', 'XML Documents', 'Plain Text CSV'], answer: 1 },
  { id: 16, topic: 'MongoDB', question: 'Which command finds all documents in a Mongoose collection?', options: ['Model.selectAll()', 'Model.find()', 'Model.get()', 'Model.fetch()'], answer: 1 },
  { id: 17, topic: 'JavaScript', question: 'What does the `Promise.all()` method do?', options: ['Rejects if any promise fails, resolves when all succeed', 'Resolves the first promise that completes', 'Executes promises sequentially', 'Converts callbacks to promises'], answer: 0 },
  { id: 18, topic: 'React', question: 'When should you use `useCallback` Hook?', options: ['To fetch API data', 'To memoize callback functions between renders', 'To manage global state', 'To measure DOM node size'], answer: 1 },
  { id: 19, topic: 'Express.js', question: 'How do you extract route parameters like `/users/:id` in Express?', options: ['req.body.id', 'req.query.id', 'req.params.id', 'req.headers.id'], answer: 2 },
  { id: 20, topic: 'MongoDB', question: 'What is an `_id` field in a MongoDB document?', options: ['A random integer', 'Primary key auto-generated unique ObjectId', 'User IP address', 'String index tag'], answer: 1 }
];

export const SAMPLE_QUESTIONS_40 = [
  ...SAMPLE_QUESTIONS_20,
  { id: 21, topic: 'HTML', question: 'What does the `defer` attribute do when loading external scripts?', options: ['Executes script immediately blocking HTML', 'Downloads script in background and executes after HTML parsing', 'Delays script execution by 5 seconds', 'Loads script only on user click'], answer: 1 },
  { id: 22, topic: 'CSS', question: 'What is the CSS specificity order from lowest to highest?', options: ['Inline > ID > Class > Element', 'Element > Class > ID > Inline', 'ID > Element > Class > Inline', 'Class > Element > ID > Inline'], answer: 1 },
  { id: 23, topic: 'CSS', question: 'Which CSS property creates a 3D perspective effect?', options: ['transform: perspective()', 'perspective', 'view-distance', 'z-index'], answer: 1 },
  { id: 24, topic: 'JavaScript', question: 'What is event bubbling in JavaScript?', options: ['Events firing at the target element only', 'Events propagating from child up through parent DOM elements', 'Events dropping from top document down to target', 'Events stopping automatically'], answer: 1 },
  { id: 25, topic: 'JavaScript', question: 'What does `Object.freeze()` do?', options: ['Deletes all object properties', 'Prevents editing, adding, or deleting properties of an object', 'Converts object to string', 'Makes object properties private'], answer: 1 },
  { id: 26, topic: 'React', question: 'What is the Virtual DOM in React?', options: ['A real DOM node copy stored on server', 'In-memory lightweight representation of actual DOM tree', 'A browser extension for debugging', 'A CSS styling engine'], answer: 1 },
  { id: 27, topic: 'React', question: 'What is the main benefit of React custom hooks?', options: ['Reusing stateful logic across multiple components', 'Replacing CSS stylesheets', 'Improving server download speed', 'Connecting directly to SQL database'], answer: 0 },
  { id: 28, topic: 'Node.js', question: 'What is `process.nextTick()` used for?', options: ['Scheduling callback for the next event loop iteration', 'Deferring code execution by 1000ms', 'Reading next file line', 'Restarting Node server'], answer: 0 },
  { id: 29, topic: 'Express.js', question: 'Which HTTP status code signifies "201 Created"?', options: ['200', '201', '404', '500'], answer: 1 },
  { id: 30, topic: 'MongoDB', question: 'What operator is used to perform full-text search indexing in MongoDB?', options: ['$search', '$text', '$regex', '$match'], answer: 1 },
  { id: 31, topic: 'JavaScript', question: 'What is a closure in JavaScript?', options: ['A function bundled with references to its surrounding lexical state', 'A method to close browser windows', 'An error handling try/catch block', 'A syntax for ending loops'], answer: 0 },
  { id: 32, topic: 'React', question: 'What does `useReducer` Hook replace for complex component state?', options: ['useEffect', 'useState', 'useRef', 'useLayoutEffect'], answer: 1 },
  { id: 33, topic: 'Node.js', question: 'Which Core module handles streaming data chunks in Node?', options: ['stream', 'buffer', 'events', 'cluster'], answer: 0 },
  { id: 34, topic: 'Express.js', question: 'Which middleware package parses JSON incoming request bodies?', options: ['express.json()', 'cors()', 'morgan()', 'helmet()'], answer: 0 },
  { id: 35, topic: 'MongoDB', question: 'Which MongoDB aggregation stage filters document stream?', options: ['$group', '$match', '$project', '$sort'], answer: 1 },
  { id: 36, topic: 'CSS', question: 'Which unit is relative to the root element font size?', options: ['em', 'rem', 'vh', '%'], answer: 1 },
  { id: 37, topic: 'JavaScript', question: 'What is the output of `[1, 2, 3] + [4, 5, 6]` in JS?', options: ['[1, 2, 3, 4, 5, 6]', '"1,2,34,5,6"', 'NaN', 'Error'], answer: 1 },
  { id: 38, topic: 'React', question: 'What is React StrictMode used for?', options: ['Strict TypeScript type checking', 'Highlighting potential problems & deprecated features in dev', 'Enforcing CSS linting', 'Securing API tokens'], answer: 1 },
  { id: 39, topic: 'Express.js', question: 'What header is sent to handle CORS issues?', options: ['Access-Control-Allow-Origin', 'Authorization', 'Content-Type', 'Accept-Encoding'], answer: 0 },
  { id: 40, topic: 'MongoDB', question: 'What feature guarantees ACID transactions across multiple MongoDB documents?', options: ['Indexes', 'Sessions and Multi-document Transactions', 'Replication Sets', 'Sharding Clusters'], answer: 1 }
];

export const ROADMAP_NODES = [
  {
    id: 'html',
    title: 'HTML5 Foundations',
    subtitle: 'Structure & Accessibility',
    description: 'Master semantic layout tags, forms, input types, meta tags, and accessibility standard WAI-ARIA.',
    status: 'completed', // completed, in-progress, unlocked, locked
    progress: 100,
    lessonsCount: 12,
    projectsCount: 2,
    quizScore: '95%',
    icon: 'FileCode',
    skills: ['Semantic HTML', 'Forms & Validation', 'SEO Meta', 'Accessibility']
  },
  {
    id: 'css',
    title: 'CSS3 & Modern Styling',
    subtitle: 'Flexbox, Grid & Animations',
    description: 'Learn modern layout systems, CSS custom properties, responsive design, and smooth transitions.',
    status: 'completed',
    progress: 100,
    lessonsCount: 16,
    projectsCount: 3,
    quizScore: '90%',
    icon: 'Palette',
    skills: ['Flexbox', 'CSS Grid', 'Tailwind', 'Keyframes']
  },
  {
    id: 'javascript',
    title: 'JavaScript Modern (ES6+)',
    subtitle: 'Async, DOM & Core Engine',
    description: 'Master closures, event loop, Promises, async/await, array transformations, and ES Modules.',
    status: 'in-progress',
    progress: 68,
    lessonsCount: 24,
    projectsCount: 4,
    quizScore: '78%',
    icon: 'Code',
    skills: ['Promises & Async', 'DOM Manipulation', 'ES6 Syntax', 'State & Events']
  },
  {
    id: 'react',
    title: 'React.js Ecosystem',
    subtitle: 'Components, Hooks & State',
    description: 'Build interactive SPAs using React Hooks (useState, useEffect, useMemo), Context API, and Router.',
    status: 'unlocked',
    progress: 25,
    lessonsCount: 28,
    projectsCount: 5,
    quizScore: 'Pending',
    icon: 'Atom',
    skills: ['React Hooks', 'Component Lifecycle', 'Router v6', 'Context API']
  },
  {
    id: 'nodejs',
    title: 'Node.js Runtime',
    subtitle: 'Server Architecture & NPM',
    description: 'Understand event-driven non-blocking I/O, file system operations, package management, and streams.',
    status: 'locked',
    progress: 0,
    lessonsCount: 18,
    projectsCount: 2,
    quizScore: 'Locked',
    icon: 'Server',
    skills: ['Event Loop', 'FS Module', 'NPM Packages', 'Streams & Buffers']
  },
  {
    id: 'express',
    title: 'Express.js Framework',
    subtitle: 'RESTful APIs & Middleware',
    description: 'Construct secure REST APIs, route controllers, authentication middlewares, and error handlers.',
    status: 'locked',
    progress: 0,
    lessonsCount: 15,
    projectsCount: 3,
    quizScore: 'Locked',
    icon: 'Layers',
    skills: ['REST Controllers', 'Custom Middleware', 'JWT Auth', 'API Routing']
  },
  {
    id: 'mongodb',
    title: 'MongoDB & Mongoose',
    subtitle: 'Database Design & Queries',
    description: 'Design NoSQL database models, schema validations, aggregation pipelines, and indexing.',
    status: 'locked',
    progress: 0,
    lessonsCount: 14,
    projectsCount: 2,
    quizScore: 'Locked',
    icon: 'Database',
    skills: ['NoSQL Schema', 'Mongoose ORM', 'Aggregation', 'Query Optimization']
  }
];

export const LEADERBOARD_DATA = [
  { rank: 1, name: 'Sarah Chen', avatar: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=150', xp: 8450, coursesCompleted: 14, weeklyRank: '+2', badge: '🏆 Top Scholar' },
  { rank: 2, name: 'David Miller', avatar: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150', xp: 7920, coursesCompleted: 12, weeklyRank: '+1', badge: '⚡ Speed Demon' },
  { rank: 3, name: 'Alex Rivera (You)', avatar: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150', xp: 6850, coursesCompleted: 10, weeklyRank: '+4', isUser: true, badge: '🔥 Streak Master' },
  { rank: 4, name: 'Elena Rostova', avatar: 'https://images.unsplash.com/photo-1517841905240-472988babdf9?w=150', xp: 6410, coursesCompleted: 9, weeklyRank: '-1', badge: '🎓 Code Ninja' },
  { rank: 5, name: 'Marcus Vance', avatar: 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=150', xp: 5980, coursesCompleted: 8, weeklyRank: '+3', badge: '🌟 Rising Star' },
  { rank: 6, name: 'Priya Sharma', avatar: 'https://images.unsplash.com/photo-1539571696357-5a69c17a67c6?w=150', xp: 5420, coursesCompleted: 7, weeklyRank: '0', badge: '💻 Tech Lead' },
  { rank: 7, name: 'Jordan Taylor', avatar: 'https://images.unsplash.com/photo-1522075469751-3a6694fb2f61?w=150', xp: 5100, coursesCompleted: 6, weeklyRank: '-2', badge: '🚀 Explorer' }
];

export const ASSESSMENT_HISTORY_DATA = [
  { id: 'AH-101', name: 'Full Stack Initial Placement Test', topic: 'Full Stack', date: '2026-08-01', marks: '34/40', percentage: 85, timeTaken: '22 mins', status: 'Passed', type: 'Initial Assessment' },
  { id: 'AH-102', name: 'HTML5 & Accessibility Evaluation', topic: 'HTML', date: '2026-08-03', marks: '19/20', percentage: 95, timeTaken: '11 mins', status: 'Passed', type: 'Weekly Assessments' },
  { id: 'AH-103', name: 'CSS Flexbox & Grid Challenge', topic: 'CSS', date: '2026-08-05', marks: '18/20', percentage: 90, timeTaken: '14 mins', status: 'Passed', type: 'Weekly Assessments' },
  { id: 'AH-104', name: 'JavaScript Async & Promises', topic: 'JavaScript', date: '2026-08-08', marks: '14/20', percentage: 70, timeTaken: '18 mins', status: 'Passed', type: 'Weekly Assessments' },
  { id: 'AH-105', name: 'Advanced React Hooks Check', topic: 'React', date: '2026-08-09', marks: '9/20', percentage: 45, timeTaken: '16 mins', status: 'Failed', type: 'Weekly Assessments' }
];

export const INDUSTRY_METRICS = {
  trendingSkills: [
    { name: 'React 19 & Next.js App Router', growth: '+42%', demand: 'Very High' },
    { name: 'TypeScript', growth: '+38%', demand: 'Essential' },
    { name: 'Tailwind CSS', growth: '+35%', demand: 'High' },
    { name: 'Node.js Microservices', growth: '+28%', demand: 'High' },
    { name: 'MongoDB Aggregations', growth: '+24%', demand: 'Moderate' }
  ],
  popularityChart: [
    { skill: 'React', score: 94 },
    { skill: 'Node.js', score: 88 },
    { skill: 'TypeScript', score: 92 },
    { skill: 'Tailwind', score: 85 },
    { skill: 'Express', score: 79 },
    { skill: 'MongoDB', score: 76 }
  ],
  topCompanies: [
    { name: 'Vercel', logo: '▲', openRoles: '42 Openings', techStack: 'Next.js, React, Node' },
    { name: 'Stripe', logo: 'S', openRoles: '85 Openings', techStack: 'React, Ruby, Node, API' },
    { name: 'Linear', logo: 'L', openRoles: '18 Openings', techStack: 'React, GraphQL, Node' },
    { name: 'Meta', logo: '∞', openRoles: '210 Openings', techStack: 'React, Relay, Express' },
    { name: 'Google', logo: 'G', openRoles: '340 Openings', techStack: 'Angular, React, Cloud' }
  ],
  salaryTrends: [
    { level: 'Junior (0-2 yrs)', salary: '$78,000 / yr' },
    { level: 'Mid-Level (2-5 yrs)', salary: '$115,000 / yr' },
    { level: 'Senior (5+ yrs)', salary: '$165,000+ / yr' },
    { level: 'Lead Architect', salary: '$210,000+ / yr' }
  ]
};

export const RESOURCES_BY_TECH = {
  HTML: [
    { id: 'res-1', type: 'Documentation', title: 'MDN HTML5 Documentation', desc: 'Official spec guide for semantic tags and modern accessibility.', url: '#', duration: 'Reading' },
    { id: 'res-2', type: 'Videos', title: 'HTML5 Crash Course for Beginners', desc: 'Comprehensive video covering forms, semantic tags, and media.', url: '#', duration: '45 mins' },
    { id: 'res-3', type: 'Projects', title: 'Responsive Portfolio Template', desc: 'Build a pure semantic HTML structure for personal portfolios.', url: '#', duration: 'Project' },
    { id: 'res-4', type: 'Practice', title: '30 HTML Form Building Challenges', desc: 'Interactive exercises testing HTML input types and validation.', url: '#', duration: '30 Qs' },
    { id: 'res-5', type: 'Cheat Sheet', title: 'HTML5 Tag Quick Reference Guide', desc: 'Downloadable PDF cheat sheet with all modern HTML tags.', url: '#', duration: 'PDF' }
  ],
  CSS: [
    { id: 'res-6', type: 'Documentation', title: 'CSS Grid & Flexbox Spec', desc: 'Complete layout guide with visual interactive diagrams.', url: '#', duration: 'Reading' },
    { id: 'res-7', type: 'Videos', title: 'Mastering Modern CSS Grid Layouts', desc: 'Step-by-step visual tutorial on grid template areas and minmax.', url: '#', duration: '1 hr 10 mins' },
    { id: 'res-8', type: 'Projects', title: 'Glassmorphism Dashboard UI', desc: 'Style a modern sleek dashboard using CSS variables and backdrop-filter.', url: '#', duration: 'Project' },
    { id: 'res-9', type: 'Practice', title: 'Flexbox Froggy & Grid Garden', desc: 'Gamified interactive exercises for CSS alignment mastery.', url: '#', duration: 'Interactive' },
    { id: 'res-10', type: 'Cheat Sheet', title: 'CSS3 Flexbox & Grid Cheat Sheet', desc: 'Essential layout properties reference printable cheat sheet.', url: '#', duration: 'PDF' }
  ],
  JavaScript: [
    { id: 'res-11', type: 'Documentation', title: 'JavaScript.info Complete Guide', desc: 'From basic fundamentals to advanced closures and event loop.', url: '#', duration: 'Reading' },
    { id: 'res-12', type: 'Videos', title: 'JavaScript Async Await & Promises Deep Dive', desc: 'Master asynchronous execution, microtasks, and Macrotasks.', url: '#', duration: '1 hr 40 mins' },
    { id: 'res-13', type: 'Projects', title: 'Interactive Kanban Task Board', desc: 'Build a drag-and-drop JS app using local storage and DOM API.', url: '#', duration: 'Project' },
    { id: 'res-14', type: 'Practice', title: '50 JS Array Method Puzzles', desc: 'Practice map, filter, reduce, find, and flatMap exercises.', url: '#', duration: 'Interactive' },
    { id: 'res-15', type: 'Cheat Sheet', title: 'ES6+ Modern JS Methods Reference', desc: 'One-page cheat sheet for destructing, arrow functions, & promises.', url: '#', duration: 'PDF' }
  ],
  React: [
    { id: 'res-16', type: 'Documentation', title: 'React 19 Official Documentation', desc: 'Learn component architecture, custom hooks, and server components.', url: '#', duration: 'Reading' },
    { id: 'res-17', type: 'Videos', title: 'React State Management & Custom Hooks', desc: 'Build scalable state architecture using Context API and custom hooks.', url: '#', duration: '2 hrs' },
    { id: 'res-18', type: 'Projects', title: 'Full AI Learning Path Dashboard', desc: 'Complete React SPA with Recharts graphs and Framer Motion.', url: '#', duration: 'Project' },
    { id: 'res-19', type: 'Practice', title: 'React Hook Debugging Challenges', desc: 'Fix infinite re-render loops and stale closure bugs in functional components.', url: '#', duration: '20 Bugfixes' },
    { id: 'res-20', type: 'Cheat Sheet', title: 'React Hooks & Lifecycle Patterns', desc: 'Handy cheat sheet for useState, useEffect, useMemo, and useRef.', url: '#', duration: 'PDF' }
  ],
  'Node.js': [
    { id: 'res-21', type: 'Documentation', title: 'Node.js v24 API Reference', desc: 'Official documentation for FS module, Streams, HTTP, and Crypto.', url: '#', duration: 'Reading' },
    { id: 'res-22', type: 'Videos', title: 'Node.js Event Loop Explained Visually', desc: 'Understand timers, poll phase, check phase, and thread pool.', url: '#', duration: '50 mins' },
    { id: 'res-23', type: 'Projects', title: 'CLI File Converter Tool', desc: 'Build an asynchronous Node CLI tool to convert Markdown to HTML.', url: '#', duration: 'Project' },
    { id: 'res-24', type: 'Practice', title: 'Node.js Stream Processing Drills', desc: 'Write memory-efficient chunk streaming pipeline scripts.', url: '#', duration: '15 Drills' },
    { id: 'res-25', type: 'Cheat Sheet', title: 'Node Core Modules Quick Sheet', desc: 'Essential FS, Path, and Stream commands at a glance.', url: '#', duration: 'PDF' }
  ],
  'Express.js': [
    { id: 'res-26', type: 'Documentation', title: 'Express.js Routing & Middleware Spec', desc: 'Learn REST endpoint structure, CORS, and error handling pipeline.', url: '#', duration: 'Reading' },
    { id: 'res-27', type: 'Videos', title: 'Building Secure REST APIs with Express & JWT', desc: 'Implement token authentication, password hashing, and input validation.', url: '#', duration: '1 hr 30 mins' },
    { id: 'res-28', type: 'Projects', title: 'E-Commerce Backend Microservice', desc: 'Build full CRUD controllers with request validation middleware.', url: '#', duration: 'Project' },
    { id: 'res-29', type: 'Practice', title: 'Express Route Error Handling Tests', desc: 'Write custom error middleware handlers for asynchronous routes.', url: '#', duration: '12 Exercises' },
    { id: 'res-30', type: 'Cheat Sheet', title: 'Express Middleware & Routing Cheat Sheet', desc: 'Quick reference for req, res, next methods and status codes.', url: '#', duration: 'PDF' }
  ],
  MongoDB: [
    { id: 'res-31', type: 'Documentation', title: 'MongoDB Manual & Mongoose Docs', desc: 'NoSQL document modeling, indexing strategies, and schema hooks.', url: '#', duration: 'Reading' },
    { id: 'res-32', type: 'Videos', title: 'MongoDB Aggregation Pipeline Mastery', desc: 'Master $match, $group, $lookup joins, and $project stages.', url: '#', duration: '1 hr 15 mins' },
    { id: 'res-33', type: 'Projects', title: 'Multi-Tenant Analytics Database', desc: 'Model schemas with relations, population, and search indexing.', url: '#', duration: 'Project' },
    { id: 'res-34', type: 'Practice', title: '25 Complex Aggregation Challenges', desc: 'Hands-on query exercises for data pipeline transformations.', url: '#', duration: '25 Queries' },
    { id: 'res-35', type: 'Cheat Sheet', title: 'MongoDB Query & Operator Cheat Sheet', desc: 'Downloadable guide for operators ($set, $push, $inc, $near).', url: '#', duration: 'PDF' }
  ]
};

export const USER_PROFILE = {
  name: 'Alex Rivera',
  title: 'Full Stack Engineering Student',
  college: 'Stanford Institute of Technology',
  email: 'alex.rivera@stanford.edu',
  avatar: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=300',
  currentDomain: 'Full Stack Development',
  streakDays: 14,
  xpLevel: 6850,
  nextLevelXp: 10000,
  levelTitle: 'Level 8 - Full Stack Specialist',
  roadmapCompletion: 52,
  certificates: [
    { id: 'cert-1', title: 'Full Stack Foundations Certificate', date: 'August 2026', credentialId: 'PATH-8849-FS', verified: true },
    { id: 'cert-2', title: 'HTML5 & Modern CSS Specialist', date: 'July 2026', credentialId: 'PATH-7731-HC', verified: true }
  ]
};
