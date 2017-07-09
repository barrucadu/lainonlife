{-# LANGUAGE OverloadedStrings #-}

import           Hakyll

main :: IO ()
main = hakyllWith defaultConfiguration $ do
  -- Templates
  match "templates/*" $
    compile templateCompiler

  -- Minify css
  match "css/*.css" $ do
    route idRoute
    compile compressCssCompiler

  -- Minify javascript
  match "js/*.js" $ do
    route idRoute
    compile copyFileCompiler

  -- Copy static files
  match "static/**" $ do
    route (dropPat "static/")
    compile copyFileCompiler

  -- Static submodule files
  let subfiles = [("font-awesome/", ["css/*", "fonts/*"])]
  mapM_ (\(p,fs) -> mapM_ (\f -> match (fromGlob $ p ++ f) $ route (dropPat p) >> compile copyFileCompiler) fs) subfiles

  -- Render pages
  match "pages/*.html" $ do
    route (dropPat "pages/")
    compile $ getResourceBody
      >>= loadAndApplyTemplate "templates/wrapper.html" (bodyField "body" `mappend` metadataField)


-------------------------------------------------------------------------------

-- | Remove some portion of the route
dropPat :: String -> Routes
dropPat pat = gsubRoute pat (const "")
