# Tzu-Wei Huang's Academic Website

This is the source code for my personal academic website, built with Hugo and the PaperMod theme.

## Local Development

To run the site locally for development:

```bash
# Clone the repository with submodules
git clone --recursive https://github.com/lanpa/lanpa.github.io.git

# Navigate to the directory
cd lanpa.github.io

# Run the development server
hugo server --config hugo.dev.toml

# Or use the production config locally
hugo server
```

The site will be available at `http://localhost:1313/`

## Deployment

The site is automatically deployed to GitHub Pages using GitHub Actions when changes are pushed to the `master` branch.

## Content Structure

- `content/about.md` - About page
- `content/cv.md` - Curriculum Vitae
- `content/academic/` - Academic content (publications, talks, teaching)
- `content/explorations/` - Personal projects and explorations
- `content/work/` - Work-related content

## Theme

This site uses the [PaperMod](https://github.com/adityatelange/hugo-PaperMod) theme for Hugo.

## Configuration

- `hugo.toml` - Production configuration (used for deployment)
- `hugo.dev.toml` - Development configuration (for local testing)
