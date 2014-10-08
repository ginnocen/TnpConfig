import FWCore.ParameterSet.Config as cms

process = cms.Process("TagProbe")

process.load('FWCore.MessageService.MessageLogger_cfi')
process.options   = cms.untracked.PSet( wantSummary = cms.untracked.bool(True) )
process.MessageLogger.cerr.FwkReport.reportEvery = 100

process.source = cms.Source("PoolSource", 
    fileNames = cms.untracked.vstring(),
)
process.maxEvents = cms.untracked.PSet( input = cms.untracked.int32(-1) )    

process.load('Configuration.StandardSequences.GeometryRecoDB_cff')
process.load('Configuration.StandardSequences.MagneticField_38T_cff')
process.load("Configuration.StandardSequences.FrontierConditions_GlobalTag_cff")
process.load("Configuration.StandardSequences.Reconstruction_cff")

process.GlobalTag.globaltag = cms.string('STARTHI53_V27::All')
#process.GlobalTag.globaltag = cms.string('GR_P_V43D::All')
process.source.fileNames = cms.untracked.vstring('root://xrootd.unl.edu//store/user/azsigmon/Powheg_DYtoMuMu_CT10nlo_5TeV_Pythia_TuneZ2star_GEN_SIM-v1/Powheg_DYtoMuMu_CT10nlo_5TeV_Pythia6_TuneZ2star_RECO-v1/0f9f0872d691759112f184ef954cde61/Powheg_DYtoMuMu_CT10nlo_5TeV_Pythia_TuneZ2star_RECO_100_1_0z9.root')
#process.source.fileNames = cms.untracked.vstring('/store/hidata/HIRun2013/PAMuon/RECO/PromptReco-v1/000/210/676/00000/FA5E61D3-E467-E211-8CBA-003048D2C0F4.root')

# Common offline event selection
process.load("HeavyIonsAnalysis.Configuration.collisionEventSelection_cff")

# Centrality for pPb
process.load('RecoHI.HiCentralityAlgos.HiCentrality_cfi')

from HeavyIonsAnalysis.Configuration.CommonFunctions_cff import *
overrideCentrality(process)

process.HeavyIonGlobalParameters = cms.PSet(
    centralityVariable = cms.string("HFtowersTrunc"),
    nonDefaultGlauberModel = cms.string(""),
    centralitySrc = cms.InputTag("pACentrality"),
#    pPbRunFlip = cms.untracked.uint32(211313)
    )

##    __  __                       
##   |  \/  |_   _  ___  _ __  ___ 
##   | |\/| | | | |/ _ \| '_ \/ __|
##   | |  | | |_| | (_) | | | \__ \
##   |_|  |_|\__,_|\___/|_| |_|___/
##                                 
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
    muonsCut     = cms.string("pt > 3 && track.isNonnull"),
    caloMuonsCut = cms.string("pt > 3"),
    tracksCut    = cms.string("pt > 3"),
)

## ==== Trigger matching
process.load("MuonAnalysis.MuonAssociators.patMuonsWithTrigger_cff")
## with some customization
process.muonMatchHLTL2.maxDeltaR = 0.3
process.muonMatchHLTL3.maxDeltaR = 0.1
from MuonAnalysis.MuonAssociators.patMuonsWithTrigger_cff import *
changeRecoMuonInput(process, "mergedMuons")
useExtendedL1Match(process)
addHLTL1Passthrough(process)
changeTriggerProcessName(process, "*") # auto-guess "*" or "HISIGNAL" / "HLT" for embedded / official MC

from MuonAnalysis.TagAndProbe.common_variables_cff import *
process.load("MuonAnalysis.TagAndProbe.common_modules_cff")

IN_ACCEPTANCE = '(abs(eta)<2.4 && pt>=15)'
TRACK_CUTS = "isTrackerMuon && track.hitPattern.trackerLayersWithMeasurement > 5 && track.hitPattern.numberOfValidPixelHits > 0"
GLB_CUTS = "isGlobalMuon && globalTrack.hitPattern.numberOfValidMuonHits > 0 && numberOfMatchedStations > 1 && globalTrack.normalizedChi2 < 10  && abs(dB) < 0.2"
QUALITY_CUTS =  "(" + GLB_CUTS + ' && ' + TRACK_CUTS + ")"

MuonIDFlags = cms.PSet(
    CaloMu	= cms.string("isCaloMuon"),
    GlobalMu	= cms.string("isGlobalMuon"),
    TrackerMu	= cms.string("isTrackerMuon"),
    TrackCuts	= cms.string(TRACK_CUTS),
    GlobalCuts	= cms.string(GLB_CUTS),
    QualityMu	= cms.string(QUALITY_CUTS)
)

process.tagMuons = cms.EDFilter("PATMuonSelector",
    src = cms.InputTag("patMuonsWithTrigger"),
    cut = cms.string(QUALITY_CUTS + ' && ' + IN_ACCEPTANCE),
)

process.oneTag  = cms.EDFilter("CandViewCountFilter", src = cms.InputTag("tagMuons"), minNumber = cms.uint32(1))

process.probeMuons = cms.EDFilter("PATMuonSelector",
    src = cms.InputTag("patMuonsWithTrigger"),
    cut = cms.string("track.isNonnull"),  # no real cut now
)

process.tpPairs = cms.EDProducer("CandViewShallowCloneCombiner",
    cut = cms.string('60 < mass < 120'),
    decay = cms.string('tagMuons@+ probeMuons@-')
)
process.onePair = cms.EDFilter("CandViewCountFilter", src = cms.InputTag("tpPairs"), minNumber = cms.uint32(1))

process.tpTree = cms.EDAnalyzer("TagProbeFitTreeProducer",
    # choice of tag and probe pairs, and arbitration
    tagProbePairs = cms.InputTag("tpPairs"),
    arbitration   = cms.string("None"),
    variables = cms.PSet(
        KinematicVariables,
	IsolationVariables,
	MuonIDVariables,
	TrackQualityVariables,
	GlobalTrackQualityVariables,
	TriggerVariables
    ),
    flags = cms.PSet(
       TrackQualityFlags,
       MuonIDFlags,
       PAMu3 = cms.string("!triggerObjectMatchesByPath('HLT_PAMu3_v*',1,0).empty()"),
       PAMu7 = cms.string("!triggerObjectMatchesByPath('HLT_PAMu7_v*',1,0).empty()"),
       PAMu12 = cms.string("!triggerObjectMatchesByPath('HLT_PAMu12_v*',1,0).empty()"),
    ),
    tagVariables = cms.PSet(
        pt = cms.string("pt"),
        eta = cms.string("eta"),
        phi = cms.string("phi"),
	tkRelIso = cms.string("(isolationR03.sumPt)/pt"),
	combRelIso = cms.string("(isolationR03.emEt + isolationR03.hadEt + isolationR03.sumPt)/pt"),
	combRelIsoPF03 = cms.string("(pfIsolationR03().sumChargedHadronPt + pfIsolationR03().sumNeutralHadronEt + pfIsolationR03().sumPhotonEt)/pt"),
	combRelIsoPF04 = cms.string("(pfIsolationR04().sumChargedHadronPt + pfIsolationR04().sumNeutralHadronEt + pfIsolationR04().sumPhotonEt)/pt"),
	l3dr = cms.string("? triggerObjectMatchesByCollection('hltL3MuonCandidates').empty() ? 999 : "+
                      " deltaR( eta, phi, " +
                      "         triggerObjectMatchesByCollection('hltL3MuonCandidates').at(0).eta, "+
                      "         triggerObjectMatchesByCollection('hltL3MuonCandidates').at(0).phi ) ")
        #nVertices   = cms.InputTag("nverticesModule"),
    ),
    tagFlags = cms.PSet(
       PAMu3 = cms.string("!triggerObjectMatchesByPath('HLT_PAMu3_v*',1,0).empty()"),
       PAMu7 = cms.string("!triggerObjectMatchesByPath('HLT_PAMu7_v*',1,0).empty()"),
       PAMu12 = cms.string("!triggerObjectMatchesByPath('HLT_PAMu12_v*',1,0).empty()"),
    ),
    pairVariables = cms.PSet(
        pt      = cms.string("pt"), 
        rapidity = cms.string("rapidity"),
    ),
    pairFlags = cms.PSet(
        BestZ = cms.InputTag("bestPairByZMass"),
    ),
    isMC           = cms.bool(False),
    addRunLumiInfo = cms.bool(True),
    addEventVariablesInfo = cms.bool(True),
    addCentralityInfo = cms.bool(True),
    allProbes      = cms.InputTag("probeMuons"),
)

process.tnpSimpleSequence = cms.Sequence(
    process.tagMuons *
    process.oneTag *
    process.probeMuons *
    process.tpPairs *
    process.onePair *
    #process.nverticesModule *
    process.bestPairByZMass * 
    process.tpTree
)

process.tagAndProbe = cms.Path( 
    process.PAcollisionEventSelection *
    process.pACentrality_step *
    process.mergedMuons *
    process.patMuonsWithTriggerSequence *
    process.tnpSimpleSequence
)

##    _____               _    _             
##   |_   _| __ __ _  ___| | _(_)_ __   __ _ 
##     | || '__/ _` |/ __| |/ / | '_ \ / _` |
##     | || | | (_| | (__|   <| | | | | (_| |
##     |_||_|  \__,_|\___|_|\_\_|_| |_|\__, |
##                                     |___/ 

## Then make another collection for standalone muons, using standalone track to define the 4-momentum
process.muonsSta = cms.EDProducer("RedefineMuonP4FromTrack",
    src   = cms.InputTag("muons"),
    track = cms.string("outer"),
)
## Match to trigger, to measure the efficiency of HLT tracking
from PhysicsTools.PatAlgos.tools.helpers import *
process.patMuonsWithTriggerSequenceSta = cloneProcessingSnippet(process, process.patMuonsWithTriggerSequence, "Sta")
process.muonMatchHLTL2Sta.maxDeltaR = 0.5
process.muonMatchHLTL3Sta.maxDeltaR = 0.5
massSearchReplaceAnyInputTag(process.patMuonsWithTriggerSequenceSta, "mergedMuons", "muonsSta")

## Define probes and T&P pairs
process.probeMuonsSta = cms.EDFilter("PATMuonSelector",
    src = cms.InputTag("patMuonsWithTriggerSta"),
    cut = cms.string("outerTrack.isNonnull"), # no real cut now
)

process.tpPairsSta = process.tpPairs.clone(decay = "tagMuons@+ probeMuonsSta@-", cut = '40 < mass < 140')

process.onePairSta = cms.EDFilter("CandViewCountFilter", src = cms.InputTag("tpPairsSta"), minNumber = cms.uint32(1))

process.staToTkMatch.maxDeltaR     = 0.3
process.staToTkMatch.maxDeltaPtRel = 2.
process.staToTkMatchNoZ.maxDeltaR     = 0.3
process.staToTkMatchNoZ.maxDeltaPtRel = 2.

process.tpTreeSta = process.tpTree.clone(
    tagProbePairs = "tpPairsSta",
    arbitration   = "OneProbe",
    variables = cms.PSet(
        KinematicVariables, 
        StaOnlyVariables,
        ## track matching variables
        tk_deltaR     = cms.InputTag("staToTkMatch","deltaR"),
        tk_deltaEta   = cms.InputTag("staToTkMatch","deltaEta"),
        tk_deltaR_NoZ   = cms.InputTag("staToTkMatchNoZ","deltaR"),
        tk_deltaEta_NoZ = cms.InputTag("staToTkMatchNoZ","deltaEta"),
    ),
    flags = cms.PSet(
        outerValidHits = cms.string("outerTrack.numberOfValidHits > 0"),
        Tk  = cms.string("track.isNonnull"),
        StaTkSameCharge = cms.string("outerTrack.isNonnull && innerTrack.isNonnull && (outerTrack.charge == innerTrack.charge)"),
        GlobalMu = cms.string("isGlobalMuon"),
        TrackerMu = cms.string("isTrackerMuon"),
    	TrackCuts = cms.string(TRACK_CUTS),
	PassingSta = cms.string("isGlobalMuon && " + TRACK_CUTS),
    ),
    tagVariables = cms.PSet(
        pt = cms.string("pt"),
        eta = cms.string("eta"),
        phi = cms.string("phi"),
	tkRelIso = cms.string("(isolationR03.sumPt)/pt"),
	combRelIso = cms.string("(isolationR03.emEt + isolationR03.hadEt + isolationR03.sumPt)/pt"),
	combRelIsoPF03 = cms.string("(pfIsolationR03().sumChargedHadronPt + pfIsolationR03().sumNeutralHadronEt + pfIsolationR03().sumPhotonEt)/pt"),
	combRelIsoPF04 = cms.string("(pfIsolationR04().sumChargedHadronPt + pfIsolationR04().sumNeutralHadronEt + pfIsolationR04().sumPhotonEt)/pt"),
        #nVertices   = cms.InputTag("nverticesModule"),
    ),
    tagFlags = cms.PSet(
       PAMu3 = cms.string("!triggerObjectMatchesByPath('HLT_PAMu3_v*',1,0).empty()"),
       PAMu7 = cms.string("!triggerObjectMatchesByPath('HLT_PAMu7_v*',1,0).empty()"),
       PAMu12 = cms.string("!triggerObjectMatchesByPath('HLT_PAMu12_v*',1,0).empty()"),
    ),
    pairVariables = cms.PSet(
        pt      = cms.string("pt"), 
        rapidity = cms.string("rapidity"),
    ),
    pairFlags = cms.PSet(),
    allProbes     = "probeMuonsSta"
)

process.tnpSimpleSequenceSta = cms.Sequence(
    process.tagMuons *
    process.oneTag *
    process.probeMuonsSta *
    process.tpPairsSta *
    process.onePairSta *
    #process.nverticesModule *
    process.staToTkMatchSequenceZ *
    process.tpTreeSta
)

process.tagAndProbeSta = cms.Path( 
    process.PAcollisionEventSelection *
    process.pACentrality_step *
    process.muonsSta *
    process.patMuonsWithTriggerSequenceSta *
    process.tnpSimpleSequenceSta
)

process.schedule = cms.Schedule(
   process.tagAndProbe, 
   process.tagAndProbeSta, 
)

process.TFileService = cms.Service("TFileService", fileName = cms.string("tnpZ_pPb_MC.root"))
