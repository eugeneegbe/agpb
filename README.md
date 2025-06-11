Flask + React app that doesn't use `create-react-app` and doesn't run a Node server alongside a Flask server. We write the Flask stuff as we normally would, and point to a JS file that we've used Webpack and Babel to prepare. Babel deals with the JSX that we're writing, and Webpack deals with the bundling and dependencies. There's no sophisticated communication between Flask and the JS stuff, but `create-react-app` doesn't have that either. This is essentially a recreation of `create-react-app` but with Flask instead of Node.

Following the [React docs](https://reactjs.org/docs/add-react-to-a-website.html) and the [Webpack docs](https://webpack.js.org/guides/getting-started/). This article on [SCSS with Webpack](https://developerhandbook.com/webpack/how-to-configure-scss-modules-for-webpack/) and the [`babel-loader` README](https://github.com/babel/babel-loader) helped as well.

To compile the src js to usable js:

```
npm run build
```

This will use Webpack and Babel to turn the code you wrote into something that can be understood.

To run the Flask server:

```
flask run
```

Be sure to go back in the Git history to see the versions of this (a) when Babel and Webpack were used separately and (b) when Babel and Webpack weren't used at all.
