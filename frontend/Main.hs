{-# LANGUAGE OverloadedStrings #-}

import           Hakyll
import qualified Language.JavaScript.Parser         as JS
import qualified Language.JavaScript.Process.Minify as JS

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
    compile compressJsCompiler

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
      >>= relativizeUrls


-------------------------------------------------------------------------------

-- | A JavaScript compiler that minifies the content
compressJsCompiler :: Compiler (Item String)
compressJsCompiler = do
  let minifyJS i = case JS.parse (itemBody i) "" of
        Right ast -> JS.renderToString (JS.minifyJS ast)
        Left  _   -> itemBody i
  s <- getResourceString
  return $ itemSetBody (minifyJS s) s

-- | Remove some portion of the route
dropPat :: String -> Routes
dropPat pat = gsubRoute pat (const "")
