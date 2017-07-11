{-# LANGUAGE DeriveGeneric #-}
{-# LANGUAGE OverloadedStrings #-}

import           Data.Aeson   (FromJSON)
import           Data.List    (stripPrefix)
import           GHC.Generics (Generic)
import           Hakyll
import           Numeric      (showFFloatAlt)

-- | Template variables.  At some point, these will be in a config file.
config :: Config
config = Config
  { defaultChannel = "cyberia"
  , icecastStatusURL = "/radio/status-json.xsl"
  , icecastStreamURLBase = "http://lainon.life:8000"
  , serverCost      = 20.39
  , thisMonthAmount = 0
  , carriedOver     = 0
  , currencySymbol  = "€"
  }


-------------------------------------------------------------------------------
-- Site generator

main :: IO ()
main = hakyllWith defaultConfiguration $ do
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

instance FromJSON Config

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
