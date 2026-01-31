#!/usr/bin/env python3
"""
Scaffold a new artifact structure.

Usage:
    python scaffold_artifact.py --name my-widget --type widget --output-dir ./artifacts
"""

import argparse
import sys
import json
from pathlib import Path


HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en" class="{dark_class}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
    <script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
    <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
    <script>
        tailwind.config = {{
            darkMode: 'class',
            theme: {{
                extend: {{
                    colors: {{
                        primary: '#3b82f6',
                        secondary: '#64748b',
                        accent: '#f472b6',
                    }}
                }}
            }}
        }}
    </script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        {custom_styles}
    </style>
</head>
<body class="bg-slate-50 dark:bg-slate-900 min-h-screen {animations}">
    <div id="root"></div>
    
    <script type="text/babel">
        {react_code}
    </script>
</body>
</html>
'''

REACT_TEMPLATES = {
    "component": '''
const App = () => {
    return (
        <div className="p-8">
            <div className="max-w-md mx-auto bg-white dark:bg-slate-800 rounded-xl shadow-lg p-6">
                <h2 className="text-2xl font-bold text-slate-900 dark:text-white mb-4">
                    Component Title
                </h2>
                <p className="text-slate-600 dark:text-slate-300">
                    Your component content goes here.
                </p>
            </div>
        </div>
    );
};

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
''',
    "page": '''
const Navbar = () => (
    <nav className="bg-white dark:bg-slate-800 shadow-sm border-b border-slate-200 dark:border-slate-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between h-16 items-center">
                <span className="text-xl font-bold text-slate-900 dark:text-white">Logo</span>
                <div className="flex space-x-4">
                    <a href="#" className="text-slate-600 dark:text-slate-300 hover:text-primary">Home</a>
                    <a href="#" className="text-slate-600 dark:text-slate-300 hover:text-primary">About</a>
                    <a href="#" className="text-slate-600 dark:text-slate-300 hover:text-primary">Contact</a>
                </div>
            </div>
        </div>
    </nav>
);

const Hero = () => (
    <section className="py-20 px-4">
        <div className="max-w-4xl mx-auto text-center">
            <h1 className="text-5xl font-bold text-slate-900 dark:text-white mb-6">
                Welcome to Your Page
            </h1>
            <p className="text-xl text-slate-600 dark:text-slate-300 mb-8">
                A beautiful, modern landing page built with React and Tailwind CSS.
            </p>
            <button className="bg-primary hover:bg-blue-600 text-white px-8 py-3 rounded-lg font-medium transition-colors">
                Get Started
            </button>
        </div>
    </section>
);

const App = () => (
    <>
        <Navbar />
        <Hero />
    </>
);

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
''',
    "widget": '''
const Widget = () => {
    const [count, setCount] = React.useState(0);
    
    return (
        <div className="p-4">
            <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-xl p-6 max-w-sm mx-auto">
                <div className="text-center">
                    <div className="text-4xl font-bold text-primary mb-2">{count}</div>
                    <p className="text-slate-500 dark:text-slate-400 mb-4">Counter Value</p>
                    <div className="flex gap-2 justify-center">
                        <button 
                            onClick={() => setCount(c => c - 1)}
                            className="px-4 py-2 bg-slate-200 dark:bg-slate-700 rounded-lg hover:bg-slate-300 dark:hover:bg-slate-600 transition-colors"
                        >
                            -
                        </button>
                        <button 
                            onClick={() => setCount(c => c + 1)}
                            className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-blue-600 transition-colors"
                        >
                            +
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

ReactDOM.createRoot(document.getElementById('root')).render(<Widget />);
''',
    "dashboard": '''
const StatCard = ({ title, value, change }) => (
    <div className="bg-white dark:bg-slate-800 rounded-xl p-6 shadow-sm">
        <p className="text-slate-500 dark:text-slate-400 text-sm">{title}</p>
        <p className="text-3xl font-bold text-slate-900 dark:text-white mt-1">{value}</p>
        <p className={`text-sm mt-2 ${change >= 0 ? 'text-green-500' : 'text-red-500'}`}>
            {change >= 0 ? '↑' : '↓'} {Math.abs(change)}%
        </p>
    </div>
);

const Dashboard = () => {
    const stats = [
        { title: 'Total Revenue', value: '$45,231', change: 12.5 },
        { title: 'Active Users', value: '2,345', change: 8.1 },
        { title: 'Conversion Rate', value: '3.2%', change: -2.4 },
        { title: 'Avg Session', value: '4m 32s', change: 15.3 },
    ];
    
    return (
        <div className="p-6">
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white mb-6">Dashboard</h1>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {stats.map((stat, i) => (
                    <StatCard key={i} {...stat} />
                ))}
            </div>
        </div>
    );
};

ReactDOM.createRoot(document.getElementById('root')).render(<Dashboard />);
'''
}


def scaffold_artifact(name: str, artifact_type: str, output_dir: str, features: list = None):
    """Create artifact scaffold."""
    features = features or []
    artifact_dir = Path(output_dir) / name
    artifact_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate HTML
    dark_class = 'dark' if 'dark-mode' in features else ''
    animations = 'transition-all duration-300' if 'animations' in features else ''
    custom_styles = ''
    
    react_code = REACT_TEMPLATES.get(artifact_type, REACT_TEMPLATES['component'])
    
    html = HTML_TEMPLATE.format(
        title=name.replace('-', ' ').title(),
        dark_class=dark_class,
        animations=animations,
        custom_styles=custom_styles,
        react_code=react_code
    )
    
    # Write files
    (artifact_dir / 'index.html').write_text(html)
    (artifact_dir / 'components.json').write_text(json.dumps({
        "name": name,
        "type": artifact_type,
        "features": features,
        "components": []
    }, indent=2))
    
    return {
        "status": "success",
        "artifact_dir": str(artifact_dir),
        "files": [
            str(artifact_dir / 'index.html'),
            str(artifact_dir / 'components.json')
        ]
    }


def main():
    parser = argparse.ArgumentParser(description='Scaffold an artifact')
    parser.add_argument('--name', required=True, help='Artifact name')
    parser.add_argument('--type', required=True, choices=['component', 'page', 'widget', 'dashboard'])
    parser.add_argument('--output-dir', required=True, help='Output directory')
    parser.add_argument('--features', help='Comma-separated features')
    
    args = parser.parse_args()
    features = args.features.split(',') if args.features else []
    
    try:
        result = scaffold_artifact(args.name, args.type, args.output_dir, features)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
