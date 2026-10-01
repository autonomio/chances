const fs = require('node:fs');
const path = require('node:path');
const {test, expect} = require('@playwright/test');
const AxeBuilder = require('@axe-core/playwright').default;
const docsMap = require('../docs-map.json');
const productDocs = require('../product-docs.json');

const contractDocument = docsMap.documents.find(
  (document) => document.source === 'docs/Developer/Documentation-System.md'
);
const contractSource = fs.readFileSync(
  path.resolve(__dirname, '..', '..', contractDocument.source),
  'utf8'
);
const contractTitle = contractSource.match(/^# (.+)$/m)[1];
const contractRoute = contractDocument.slug.replace(/^\//, '');

test('desktop documentation surface matches the shared contract', async ({page}) => {
  await page.goto(`${contractRoute}?docusaurus-theme=light`);
  await expect(page.locator('h1')).toHaveText(contractTitle);
  await expect(page.locator('.navbar__link')).toHaveText([
    'Home',
    'Overview',
    'Guides',
    'Reference',
    'Developer',
    'Packages',
    'GitHub',
  ]);
  await expect(page.locator('a', {hasText: 'Edit this page'})).toHaveAttribute(
    'href',
    `${productDocs.sourceRepoUrl}/edit/${productDocs.sourceBranch}/${contractDocument.source}`
  );
  const geometry = await page.locator('.theme-doc-markdown').evaluate((element) => ({
    width: element.getBoundingClientRect().width,
    font: getComputedStyle(element).fontFamily,
    size: getComputedStyle(element).fontSize,
    navbar: document.querySelector('.navbar').getBoundingClientRect().height,
    overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
  }));
  expect(geometry.width).toBeLessThanOrEqual(680);
  expect(geometry.font).toContain('IBM Plex Sans');
  expect(geometry.size).toBe('17px');
  expect(geometry.navbar).toBeGreaterThanOrEqual(55);
  expect(geometry.navbar).toBeLessThanOrEqual(57);
  expect(geometry.overflow).toBeLessThanOrEqual(1);
  const accessibility = await new AxeBuilder({page}).withTags(['wcag2a', 'wcag2aa']).analyze();
  expect(accessibility.violations).toEqual([]);
});

test('search and mobile behavior remain functional', async ({page}) => {
  await page.goto('?docusaurus-theme=light');
  await page.locator('input[aria-label="Search"]').fill(contractTitle);
  await expect(page.locator('[role="listbox"]')).toBeVisible();
  await expect(page.locator('[role="listbox"]')).toContainText(contractTitle);

  await page.setViewportSize({width: 390, height: 844});
  await page.goto(`${contractRoute}?docusaurus-theme=dark`);
  await expect(page.locator('.navbar__toggle')).toBeVisible();
  await expect(page.locator('.theme-doc-sidebar-container')).toBeHidden();
  const mobile = await page.evaluate(() => ({
    theme: document.documentElement.dataset.theme,
    overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
  }));
  expect(mobile.theme).toBe('dark');
  expect(mobile.overflow).toBeLessThanOrEqual(1);
});

const representativePages = [
  {role: 'home', slug: '/'},
  {role: 'category', slug: docsMap.sections[0].slug},
  ...['guides', 'reference', 'developer', 'packages'].map((section) => ({
    role: section,
    slug: docsMap.documents.find((document) => document.dest.startsWith(`${section}/`)).slug,
  })),
];

for (const viewport of [
  {name: 'desktop', width: 1440, height: 900},
  {name: 'mobile', width: 390, height: 844},
]) {
  for (const theme of ['light', 'dark']) {
    for (const representative of representativePages) {
      test(`${representative.role} ${viewport.name} ${theme} meets layout and accessibility`, async ({page}, testInfo) => {
        const errors = [];
        page.on('pageerror', (error) => errors.push(error.message));
        page.on('console', (message) => {
          if (message.type() === 'error') errors.push(message.text());
        });
        await page.setViewportSize({width: viewport.width, height: viewport.height});
        await page.goto(`${representative.slug.replace(/^\//, '')}?docusaurus-theme=${theme}`);
        await expect(page.locator('h1')).toBeVisible();
        await page.evaluate(async () => { await document.fonts.ready; });
        await expect(page.locator('html')).toHaveAttribute('data-theme', theme);
        const geometry = await page.evaluate(() => ({
          overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
          navbar: document.querySelector('.navbar').getBoundingClientRect().height,
          paper: getComputedStyle(document.documentElement).getPropertyValue('--autonomio-paper').trim(),
        }));
        expect(geometry.overflow).toBeLessThanOrEqual(1);
        expect(geometry.navbar).toBeGreaterThanOrEqual(55);
        expect(geometry.navbar).toBeLessThanOrEqual(57);
        expect(geometry.paper.toLowerCase()).toBe(theme === 'light' ? '#f8f8f8' : '#121212');
        if (viewport.name === 'mobile') {
          await expect(page.locator('.navbar__toggle')).toBeVisible();
          await expect(page.locator('.theme-doc-sidebar-container')).toBeHidden();
        } else {
          await expect(page.locator('.navbar__toggle')).toBeHidden();
          await expect(page.locator('.theme-doc-sidebar-container')).toBeVisible();
        }
        await page.keyboard.press('Tab');
        await expect(page.getByRole('link', {name: 'Skip to main content'})).toBeFocused();
        await page.keyboard.press('Enter');
        const accessibility = await new AxeBuilder({page}).withTags(['wcag2a', 'wcag2aa']).analyze();
        fs.writeFileSync(testInfo.outputPath('accessibility.json'), JSON.stringify(accessibility, null, 2));
        expect(accessibility.violations.map((violation) => ({
          id: violation.id, impact: violation.impact,
          failures: [...new Set(violation.nodes.map((node) => node.failureSummary))],
        }))).toEqual([]);
        expect(errors).toEqual([]);
        await page.screenshot({path: testInfo.outputPath(`${representative.role}-${viewport.name}-${theme}.png`), fullPage: true});
      });
    }
  }
}

test('mobile drawer and on-page contents respond to keyboard activation', async ({page}) => {
  await page.setViewportSize({width: 390, height: 844});
  await page.goto(`${contractRoute}?docusaurus-theme=light`);
  const toggle = page.getByRole('button', {name: 'Toggle navigation bar'});
  await toggle.focus();
  await page.keyboard.press('Enter');
  await expect(page.locator('.navbar-sidebar')).toBeVisible();
  await expect(page.locator('.navbar-sidebar').getByRole('link', {name: 'Guides', exact: true}).first()).toBeVisible();
  await page.getByRole('button', {name: 'Close navigation bar'}).click();
  await expect(page.locator('.navbar-sidebar')).not.toBeVisible();
  const toc = page.locator('.theme-doc-toc-mobile button');
  await toc.focus();
  await page.keyboard.press('Enter');
  await expect(page.locator('.theme-doc-toc-mobile a').first()).toBeVisible();
});

test('full search page exposes indexed product documentation', async ({page}) => {
  await page.goto(`search?q=${encodeURIComponent(contractTitle)}`);
  await expect(page.locator('h1')).toContainText('Search');
  const result = page.getByRole('link', {name: contractTitle, exact: true}).first();
  await expect(result).toBeVisible();
  await result.click();
  await expect(page.locator('h1')).toHaveText(contractTitle);
});
