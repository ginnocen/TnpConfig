import FWCore.ParameterSet.Config as cms

process = cms.Process("TagProbe")

process.load('FWCore.MessageService.MessageLogger_cfi')
process.options   = cms.untracked.PSet( wantSummary = cms.untracked.bool(True) )
process.MessageLogger.cerr.FwkReport.reportEvery = 100

process.source = cms.Source("PoolSource", 
    fileNames = cms.untracked.vstring(),
)
process.maxEvents = cms.untracked.PSet( input = cms.untracked.int32(100) )    


process.load('Configuration.StandardSequences.GeometryRecoDB_cff')
process.load('Configuration.StandardSequences.MagneticField_AutoFromDBCurrent_cff')
process.load("Configuration.StandardSequences.FrontierConditions_GlobalTag_cff")
process.load("Configuration.StandardSequences.Reconstruction_cff")

import os
if   "CMSSW_5_3_" in os.environ['CMSSW_VERSION']:
    process.GlobalTag.globaltag = cms.string('START53_V27::All')
    process.source.fileNames = [
        'file:/afs/cern.ch/work/g/ginnocen/public/38291323-E567-E211-8DD9-5404A63886C5.root',
    ]
elif "CMSSW_5_2_" in os.environ['CMSSW_VERSION']:
    process.GlobalTag.globaltag = cms.string('GR_P_V39_AN1::All')
    process.source.fileNames = [
        '/store/data/Run2012A/MuOnia/AOD/PromptReco-v1/000/191/226/645E9BE9-FC87-E111-9D30-5404A63886C5.root',
        '/store/data/Run2012A/MuOnia/AOD/PromptReco-v1/000/191/226/60C36C17-0188-E111-8B3D-5404A638868F.root',
        '/store/data/Run2012A/MuOnia/AOD/PromptReco-v1/000/191/226/5E384785-F087-E111-A8CB-BCAEC518FF80.root',
        '/store/data/Run2012A/MuOnia/AOD/PromptReco-v1/000/191/226/5C605E9F-F887-E111-A540-00237DDC5CB0.root',
        '/store/data/Run2012A/MuOnia/AOD/PromptReco-v1/000/191/226/5C0DCA92-CE87-E111-A539-5404A63886C6.root',
        '/store/data/Run2012A/MuOnia/AOD/PromptReco-v1/000/191/226/5A856F46-1888-E111-A3A5-BCAEC5329700.root',
        '/store/data/Run2012A/MuOnia/AOD/PromptReco-v1/000/191/226/5271187F-DF87-E111-ADDB-BCAEC518FF7C.root',
    ]
else: raise RuntimeError, "Unknown CMSSW version %s" % os.environ['CMSSW_VERSION']



## ==== Fast Filters ====
process.goodVertexFilter = cms.EDFilter("VertexSelector",
    src = cms.InputTag("offlinePrimaryVertices"),
    cut = cms.string("!isFake && ndof > 4 && abs(z) <= 25 && position.Rho <= 2"),
    filter = cms.bool(True),
)
process.noScraping = cms.EDFilter("FilterOutScraping",
    applyfilter = cms.untracked.bool(True),
    debugOn = cms.untracked.bool(False), ## Or 'True' to get some per-event info
    numtrack = cms.untracked.uint32(10),
    thresh = cms.untracked.double(0.25)
)
process.fastFilter = cms.Sequence(process.goodVertexFilter + process.noScraping)

process.load("HLTrigger.HLTfilters.triggerResultsFilter_cfi")
process.triggerResultsFilter.triggerConditions = cms.vstring( 'HLT_PAMu3_v*' )
process.triggerResultsFilter.l1tResults = ''
process.triggerResultsFilter.throw = True
process.triggerResultsFilter.hltResults = cms.InputTag( "TriggerResults", "", "HLT" )
process.HLTMu   = process.triggerResultsFilter.clone(triggerConditions = [ 'HLT_PAMu3_v*' ])

## ==== Merge CaloMuons and Tracks into the collection of reco::Muons  ====
from RecoMuon.MuonIdentification.calomuons_cfi import calomuons;
process.mergedMuons = cms.EDProducer("CaloMuonMerger",
    mergeTracks = cms.bool(True),
    mergeCaloMuons = cms.bool(False), # AOD
    muons     = cms.InputTag("muons"), 
    caloMuons = cms.InputTag("calomuons"),
    tracks    = cms.InputTag("generalTracks"),
    minCaloCompatibility = calomuons.minCaloCompatibility,
    ## Apply some minimal pt cut
    muonsCut     = cms.string("track.isNonnull && pt > 1"),
    caloMuonsCut = cms.string("pt > 1"),
    tracksCut    = cms.string("pt > 1"),
)

## ==== Trigger matching
process.load("MuonAnalysis.MuonAssociators.patMuonsWithTrigger_cff")
## with some customization
from MuonAnalysis.MuonAssociators.patMuonsWithTrigger_cff import *
changeRecoMuonInput(process, "mergedMuons")
useExtendedL1Match(process)
addHLTL1Passthrough(process)

IN_ACCEPTANCE = "((abs(eta) <= 1.3 && pt > 3.3) || (1.3 < abs(eta) <= 2.2 && p > 2.9) || (2.2 < abs(eta) <= 2.4 && pt > 0.8))"
TRACK_CUTS = "(track.hitPattern.trackerLayersWithMeasurement > 5 && track.normalizedChi2 < 1.8 && track.hitPattern.pixelLayersWithMeasurement > 0 && abs(dB) < 3 && abs(track.dz) < 30)"
GLB_CUTS = "(isTrackerMuon && muonID('TrackerMuonArbitrated') && muonID('TMOneStationTight'))"
QUALITY_CUTS =  "(" + GLB_CUTS + " && " + TRACK_CUTS + ")"


MuonQualityFlagspPb = cms.PSet(
    TrackCuts	= cms.string(TRACK_CUTS),
    GlobalCuts	= cms.string(GLB_CUTS),
    QualityMu	= cms.string(QUALITY_CUTS)
)


from MuonAnalysis.TagAndProbe.common_variables_cff import *
process.load("MuonAnalysis.TagAndProbe.common_modules_cff")

process.tagMuons = cms.EDFilter("PATMuonSelector",
    src = cms.InputTag("patMuonsWithTrigger"),
    cut = cms.string(QUALITY_CUTS+ "&&"+ IN_ACCEPTANCE+"&&(!triggerObjectMatchesByPath('HLT_PAMu3_v*',1,0).empty())"),
)

process.oneTag  = cms.EDFilter("CandViewCountFilter", src = cms.InputTag("tagMuons"), minNumber = cms.uint32(1))

process.probeMuons = cms.EDFilter("PATMuonSelector",
    src = cms.InputTag("patMuonsWithTrigger"),
    cut = cms.string("track.isNonnull")
)

process.tpPairs = cms.EDProducer("CandViewShallowCloneCombiner",
    cut = cms.string('2.8 < mass < 3.4'),
    decay = cms.string('tagMuons@+ probeMuons@-')
)
process.onePair = cms.EDFilter("CandViewCountFilter", src = cms.InputTag("tpPairs"), minNumber = cms.uint32(1))

from MuonAnalysis.TagAndProbe.muon.tag_probe_muon_extraIso_cff import ExtraIsolationVariables

process.tpTree = cms.EDAnalyzer("TagProbeFitTreeProducer",
    # choice of tag and probe pairs, and arbitration
    tagProbePairs = cms.InputTag("tpPairs"),
    arbitration   = cms.string("None"),
    # probe variables: all useful ones
    variables = cms.PSet(
        #AllVariables,
        KinematicVariables,
        IsolationVariables,
	    MuonIDVariables,
	    TrackQualityVariables,
	    GlobalTrackQualityVariables,
	    TriggerVariables,
    ),
    flags = cms.PSet(
       TrackQualityFlags,
       HFHIPhysicsFlagsTrigger,
       MuonQualityFlagspPb,
       MuonIDFlags,
       Acc_JPsi = cms.string(IN_ACCEPTANCE),
    ),
    tagVariables = cms.PSet(
        pt  = cms.string('pt'),
        eta = cms.string('eta'),
        phi = cms.string('phi'),
        nVertices = cms.InputTag("nverticesModule"),
        l1rate = cms.InputTag("l1rate"),
        bx     = cms.InputTag("l1rate","bx"),
    ),
    tagFlags     = cms.PSet(
        HFHIPhysicsFlagsTrigger,
    ),
    pairVariables = cms.PSet(
        pt      = cms.string("pt"), 
        rapidity = cms.string("rapidity"),
    ),
    pairFlags = cms.PSet(),
    isMC           = cms.bool(False),
    addRunLumiInfo = cms.bool(True),
    #allProbes      = cms.InputTag("probeMuons"),
)

process.load("MuonAnalysis.TagAndProbe.muon.tag_probe_muon_extraIso_cfi")

process.tnpSimpleSequence = cms.Sequence(
    process.tagMuons +
    process.oneTag     +
    process.probeMuons +
    process.tpPairs    +
    process.onePair    +
    process.l1rate +
    process.tpTree
)

process.tagAndProbe = cms.Path( 
    process.fastFilter +
    process.HLTMu    +
    process.mergedMuons                 *
    process.patMuonsWithTriggerSequence *
    process.tnpSimpleSequence
)

process.TFileService = cms.Service("TFileService", fileName = cms.string("tnpJPsi_Data.root"))
