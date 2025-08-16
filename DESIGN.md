# Design Document: Tzu-Wei Huang's Academic Website

## Overview

This document serves as a design guideline for Tzu-Wei Huang's personal website. The website is built using Hugo static site generator with the Hugo Profile theme, with some sections also using the PaperMod theme. It serves as a personal academic portfolio showcasing research, publications, teaching materials, and personal projects.

## Project Structure

### Core Components

1. **Content Organization**
   - `/content/` - Contains all the website's content organized in markdown files
   - `/static/` - Stores static assets (images, CSS, JS)
   - `/layouts/` - Contains custom HTML templates that override theme defaults
   - `/themes/` - Contains the Hugo themes (hugo-profile and PaperMod)

2. **Configuration Files**
   - `hugo.toml` - Production configuration
   - `hugo.dev.toml` - Development configuration
   - `dev-server.sh` - Script for local development server

3. **Build and Deployment**
   - Uses GitHub Actions for CI/CD
   - Automated deployment to GitHub Pages

## Content Structure

The site content is organized into several main sections:

1. **Academic** (`/content/academic/`)
   - Publications
   - Talks
   - Teaching materials

2. **Academic Videos** (`/content/academic-videos/`)
   - Course-related video materials
   - Tutorial videos
   - Organized by course code

3. **Explorations** (`/content/explorations/`)
   - Travel
   - Cycling
   - Exploratory work

4. **Work** (`/content/work/`)
   - Personal projects
   - Industry insights

5. **Fixing** (`/content/fixing/`)
   - DIY projects
   - Repair guides
   - Repair guides

6. **Velodash** (`/content/velodash/`)
   - Cycling-related content
   - "環騎台北" (Cycling around Taipei) project

## Layout Structure

The `/layouts/` directory contains custom HTML templates organized by section:

1. **Default** (`/layouts/_default/`)
   - Base templates for standard pages
   - List templates for section indexes

2. **Section-specific Layouts**
   - `/layouts/academic/` - Academic section layouts
   - `/layouts/academic-videos/` - Academic videos section layouts
   - `/layouts/explorations/` - Explorations section layouts
   - `/layouts/work/` - Work section layouts
   - `/layouts/fixing/` - DIY & Fixing section layouts
   - `/layouts/cycling-videos/` - Cycling videos section layouts
   - `/layouts/velodash/` - Velodash section layouts

3. **Partial Templates** (`/layouts/partials/`)
   - Reusable component templates
   - Header, footer, and navigation components
   - Project section templates (`/layouts/partials/projects/`)
     - `list-content.html` - Common template for project section listing pages (used by Academic, Academic Videos, Explorations, Work, DIY & Fix, Cycling Videos)
     - `single-content.html` - Common template for single project pages (used by all content types)

4. **Shortcodes** (`/layouts/shortcodes/`)
   - Custom Hugo shortcodes for content enhancement

## Styling and Assets

1. **CSS**
   - `/static/css/` - Custom CSS files
   - Theme CSS overrides

2. **JavaScript**
   - `/static/js/` - Custom JavaScript files
   - Language toggle functionality

3. **Images**
   - `/static/images/` - Site images and media

## Multilingual Support

The site features a simple language toggle system:
- Uses custom JavaScript (`/static/js/title-i18n.js`)
- Toggle button in the top-right corner (中/EN)
- Content is managed through i18n files in the `/i18n/` directory

## Local Development

1. **Setup**
   ```bash
   git clone --recursive https://github.com/lanpa/lanpa.github.io.git
   cd lanpa.github.io
   ```

2. **Development Server**
   ```bash
   ./dev-server.sh
   ```
   Or manually:
   ```bash
   hugo server --config hugo.dev.toml
   ```

3. **Building for Production**
   Avoid this locally.
   ```bash
   hugo --cleanDestinationDir
   ```

## Deployment Process

1. **GitHub Actions**
   - Automated builds triggered on push to `master` branch
   - Outputs to the `/public` directory
   - Deployed to GitHub Pages

2. **Manual Deployment**
   - Build the site with `hugo --cleanDestinationDir`
   - Deploy `/public` directory contents to web server

## Design Principles

1. **Content-First Approach**
   - Focus on clear presentation of academic content
   - Minimal design that emphasizes readability

2. **Separation of Concerns**
   - Content (markdown files) separate from presentation (templates)
   - Configuration separate from content

3. **Modularity**
   - Independent sections with their own layouts and styling
   - Reusable components via Hugo partials
   - Shared implementation for project sections (Academic, Academic Videos, Explorations, Work, DIY & Fix, Cycling Videos)

4. **Responsive Design**
   - Mobile-friendly layout
   - Adaptive content presentation

5. **Performance Optimization**
   - Static site generation for fast loading
   - Optimized image assets
   - Minimal JavaScript usage

## Future Development Guidelines

1. **Adding New Content**
   - Place new markdown files in the appropriate `/content/` subdirectory
   - Use consistent frontmatter format (title, date, draft status)
   - Consider using Hugo archetypes for new content types

2. **Creating New Sections**
   - Add section directory under `/content/`
   - Create `_index.md` for section landing page
   - Add custom layouts in `/layouts/` if needed
   - Update navigation in `hugo.toml`

3. **Modifying Layouts**
   - Make incremental changes to avoid breaking existing content
   - Test changes locally before deployment
   - Consider mobile and desktop views

4. **Theme Customization**
   - Prefer overriding theme templates in `/layouts/` rather than modifying theme files
   - Document theme customizations

5. **Performance Considerations**
   - Optimize images before adding to static assets
   - Minimize external dependencies
   - Use Hugo's built-in asset pipeline for CSS/JS

## Maintenance Tasks

1. **Regular Updates**
   - Keep Hugo and themes updated
   - Review and update content for accuracy

2. **Backup Strategy**
   - Ensure regular backups of the repository
   - Consider periodic exports of the built site

3. **Monitoring**
   - Use Google Analytics (ID: G-WBXXLKTC4L) to track usage
   - Monitor site performance and user experience

## Technical Specifications

1. **Hugo Version**
   - Use Hugo Extended version for SASS/SCSS support
   - Maintain compatibility with latest stable release

2. **Browser Support**
   - Modern browsers (Chrome, Firefox, Safari, Edge)
   - Responsive design for mobile devices

3. **Performance Targets**
   - Page load time < 2 seconds
   - Google PageSpeed score > 90

## Documentation

1. **README.md**
   - Basic project information
   - Setup and local development instructions

2. **DESIGN.md (this document)**
   - Comprehensive design guidelines
   - Project structure and organization

3. **Inline Comments**
   - Document complex templates or functions
   - Explain non-obvious configuration settings

## Contact and Support

For questions or issues regarding the website design and development, contact:
- GitHub: [github.com/lanpa](http://github.com/lanpa)

