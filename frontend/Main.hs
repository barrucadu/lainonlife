{-# LANGUAGE DeriveGeneric #-}
{-# LANGUAGE MultiWayIf #-}
{-# LANGUAGE OverloadedStrings #-}
{-# LANGUAGE QuasiQuotes #-}

import qualified Data.Aeson            as A
import qualified Data.Aeson.Types      as A
import qualified Data.ByteString       as BS
import           Data.Char             (toLower)
import qualified Data.HashMap.Lazy     as H
import           Data.List             (stripPrefix)
import           GHC.Generics          (Generic)
import           Hakyll
import           Numeric               (showFFloatAlt)
import qualified System.Console.Docopt as D
import           System.Environment    (getArgs)
import           System.Exit           (exitFailure)
import           System.IO.Error       (catchIOError)
import           Text.Read             (readMaybe)

-- | Command-line arguments
usage :: D.Docopt
usage = [D.docopt|
frontend - generate the lainon.life static assets

Usage:
  frontend (build | clean | rebuild | watch [--host=HOST] [--port=PORT]) [--verbose] [--config=FILE]

Options:
  --verbose        Run in verbose mode
  --config=FILE    Path to the configuration file  [default: config.json]
  --host=HOST      Host to listen on               [default: localhost]
  --port=PORT      Port to listen on               [default: 3000]

Commands:
  build            Generate the site
  clean            Clean up and remove cache
  rebuild          Clean and build again
  watch            Autocompile on changes and start a preview server.
|]

-- | Parse the command-line arguments and build (or whatever) the site.
main :: IO ()
main = do
  args <- D.parseArgsOrExit usage =<< getArgs

  let die s = putStrLn s >> exitFailure

  case hakyllOptsFor args of
    Just hakyllOpts -> do
      let configFile = D.getArgWithDefault args "config.json" (D.longOption "config")
      configBytes <- BS.readFile configFile `catchIOError` \_ -> die "--config must be a site configuration file"
      let config = do
            -- accepted config is json in the form { "template": config_obj, ... }
            A.Object o  <- A.decodeStrict configBytes
            val         <- H.lookup "template" o
            A.Success c <- pure (A.fromJSON val)
            pure c
      case config of
        Just config -> hakyllWithArgs defaultConfiguration hakyllOpts (renderSite config)
        Nothing     -> die "--config must be a site configuration file"
    Nothing -> die "cannot understand command-line arguments"

-- | Turn the command-line arguments into Hakyll options.
hakyllOptsFor :: D.Arguments -> Maybe Options
hakyllOptsFor args = Options (args `D.isPresent` D.longOption "verbose")
  <$> (if | args `D.isPresent` D.command "build"   -> Just Build
          | args `D.isPresent` D.command "clean"   -> Just Clean
          | args `D.isPresent` D.command "rebuild" -> Just Rebuild
          | args `D.isPresent` D.command "watch"   ->
            let host = D.getArgWithDefault args "localhost" (D.longOption "host")
                port = D.getArgWithDefault args "3000" (D.longOption "port")
            in (\p -> Watch host p False) <$> readMaybe port)

-------------------------------------------------------------------------------
-- Site generator

-- | Build (or whatever) the site.
renderSite :: Config -> Rules ()
renderSite config = do
  let cfg = cfgContext config

  -- Templates
  match "templates/*" $
    compile templateCompiler

  -- Minify css
  match "css/*.css" $ do
    route idRoute
    compile $ getResourceBody
      >>= applyAsTemplate cfg
      >>= pure . fmap compressCss

  -- Minify javascript
  match "js/*.js" $ do
    route idRoute
    compile $ getResourceBody
      >>= applyAsTemplate cfg

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
      >>= applyAsTemplate cfg
      >>= loadAndApplyTemplate "templates/wrapper.html" (bodyField "body" `mappend` metadataField)


-------------------------------------------------------------------------------
-- Configuration

-- | Site configuration.
data Config = Config
  { defaultChannel :: String
  -- ^ The channel to start playing.
  , icecastStatusURL :: String
  -- ^ The public URL of the status-json.xsl file.
  , icecastStreamURLBase :: String
  -- ^ The public URL base of the streams.
  , serverCost :: Double
  -- ^ The monthly cost of the server.
  , thisMonthAmount :: Double
  -- ^ The amount donated so far this month.
  , carriedOver :: Double
  -- ^ The amount carried over from previous months.
  , currencySymbol :: String
  -- ^ The currency symbol for the server bill.
  } deriving Generic

instance A.FromJSON Config where
  parseJSON = A.genericParseJSON A.defaultOptions { A.fieldLabelModifier = map toLower . A.camelTo2 '_' }

-- | Turn the configuration into a Hakyll context.
cfgContext :: Config -> Context String
cfgContext conf = mconcat . map (uncurry constField) $
    [ ("default_channel",  defaultChannel conf)
    , ("icecast_status_url",      icecastStatusURL     conf)
    , ("icecast_stream_url_base", icecastStreamURLBase conf)
    , ("server_cost",         showAmount (serverCost conf))
    , ("this_month_amount",   showAmount (thisMonthAmount conf))
    , ("this_month_progress", show (percent balance (serverCost conf)))
    ] ++ [("this_month_paid",     "yes")                         | surplus >= 0]
      ++ [("surplus_amount",      showAmount surplus)            | surplus > 0]
      ++ [("carried_over_amount", showAmount (carriedOver conf)) | carriedOver conf > 0]
  where
    balance = carriedOver conf + thisMonthAmount conf
    surplus = balance - serverCost conf
    percent x y = max 0 (min 100 (x / y * 100))

    showAmount amount =
      let strAmount = showFFloatAlt (Just 2) amount ""
      in currencySymbol conf ++ stripSuffix ".00" strAmount


-------------------------------------------------------------------------------
-- Utilities

-- | Remove some portion of the route
dropPat :: String -> Routes
dropPat pat = gsubRoute pat (const "")

-- | Strip a suffix from a list, leaving it unaltered if that is not a
-- suffix.
stripSuffix :: Eq a => [a] -> [a] -> [a]
stripSuffix suff xs = maybe xs reverse (stripPrefix (reverse suff) (reverse xs))
