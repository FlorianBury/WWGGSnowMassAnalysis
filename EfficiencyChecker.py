Bfrom bamboo.analysismodules import AnalysisModule, HistogramsModule

class CMSPhase2SimRTBModule(AnalysisModule):
    """ Base module for processing Phase2 flat trees """
 65;6003;1c   def __init__(self, args):
        super(CMSPhase2SimRTBModule, self).__init__(args)
        self._h_genwcount = {}
    def prepareTree(self, tree, sample=None, sampleCfg=None):
        from bamboo.treedecorators import decorateCMSPhase2SimTree
        from bamboo.dataframebackend import DataframeBackend
        t = decorateCMSPhase2SimTree(tree, isMC=True)
        be, noSel = DataframeBackend.create(t)
        from bamboo.root import gbl
        self._h_genwcount[sample] = be.rootDF.Histo1D(
                gbl.ROOT.RDF.TH1DModel("h_count_genweight", "genweight sum", 1, 0., 1.),
                "_zero_for_stats",
                "genweight"
                )
        return t, noSel, be, tuple()
    def mergeCounters(self, outF, infileNames, sample=None):
        outF.cd()
        self._h_genwcount[sample].Write("h_count_genweight")
    def readCounters(self, resultsFile):
        return {"sumgenweight": resultsFile.Get("h_count_genweight").GetBinContent(1)}

class CMSPhase2SimRTBHistoModule(CMSPhase2SimRTBModule, HistogramsModule):
    """ Base module for producing plots from Phase2 flat trees """
    def __init__(self, args):
        super(CMSPhase2SimRTBHistoModule, self).__init__(args)


################################
## An analysis module example ##
################################

class SnowmassExample(CMSPhase2SimRTBHistoModule):
    def definePlots(self, t, noSel, sample=None, sampleCfg=None):
        from bamboo.plots import Plot, CutFlowReport
        from bamboo.plots import EquidistantBinning as EqB
        from bamboo import treefunctions as op
        
        #count no of events here 

        noSel = noSel.refine("withgenweight", weight=t.genweight)

        plots = []

        #H->gg 

        #selection of photons with eta in the detector acceptance
        photons = op.select(t.gamma, lambda ph : op.AND(op.abs(ph.eta)<2.5, ph.pt >25.)) 
        #sort photons by pT 
        sort_ph = op.sort(photons, lambda ph : -ph.pt)

        #selection of photons with loose ID        
        idPhotons = op.select(sort_ph, lambda ph : ph.idpass & (1<<0))
 
        #selection: 2 photons (at least) in an event with invariant mass within [100,150]
        hasTwoPh = noSel.refine("hasMassPhPh", cut= op.AND(
            (op.rng_len(idPhotons) >= 2), 
            (op.in_range(100, op.invariant_mass(idPhotons[0].p4, idPhotons[1].p4), 180)) 
        ))
        
        mGG = op.invariant_mass(idPhotons[0].p4, idPhotons[1].p4)
        #hGG = op.sum(sorted_ph[0].p4, sorted_ph[1].p4)
        
        #H->WW->2q1l1nu
        
        electrons = op.select(t.elec, lambda el : op.AND(
            el.pt > 10., op.abs(el.eta) < 2.5
        ))
        clElectrons = op.select(electrons, lambda el : op.NOT(op.rng_any(idPhotons, lambda ph : op.deltaR(el.p4, ph.p4) > 0.4))) #apply a deltaR 
        sort_el = op.sort(clElectrons, lambda el : -el.pt)        
        idElectrons = op.select(sort_el, lambda el : el.idpass & (1<<0) )  #apply loose ID  
        
        #clElectrons = op.select(idElectrons, lambda el : op.NOT(op.rng_any(idPhotons, lambda ph : op.deltaR(el.p4, ph.p4) < 0.4))) #apply a deltaR 
        
        muons = op.select(t.muon, lambda mu : op.AND(
            mu.pt > 10., op.abs(mu.eta) < 2.5
        ))
        clMuons = op.select(muons, lambda mu : op.NOT(op.rng_any(idPhotons, lambda ph : op.deltaR(mu.p4, ph.p4) > 0.4 )))
        sort_mu = op.sort(clMuons, lambda mu : -mu.pt)
        idMuons = op.select(sort_mu, lambda mu : mu.idpass & (1<<2) ) #apply loose ID  

              
        ##select jets with pt>25 GeV end eta in the detector acceptance
        jets = op.select(t.jetpuppi, lambda jet : op.AND(jet.pt > 25., op.abs(jet.eta) < 2.4))
        clJets = op.select(jets, lambda j : op.AND(
            op.NOT(op.rng_any(idPhotons, lambda ph : op.deltaR(ph.p4, j.p4) > 0.4) ),
            op.NOT(op.rng_any(idElectrons, lambda el : op.deltaR(el.p4, j.p4) > 0.4) ),  
            op.NOT(op.rng_any(idMuons, lambda mu : op.deltaR(mu.p4, j.p4) > 0.4) ),
        ))

        sort_jets = op.sort(clJets, lambda jet : -jet.pt)        
        
        idJets = op.select(sort_jets, lambda j : j.idpass & (1<<2))

         
        mJets= op.invariant_mass(cleanedJets[0].p4, cleanedJets[1].p4)
        #hJets = op.sum(cleanedJets[0].p4, cleanedJets[1].p4)
       
        #missing transverse energy
        met = op.select(t.metpuppi)      

        #selections
         
        sel1_p = noSel.refine("2Photon", cut = op.AND((op.rng_len(sort_ph) >= 2), (sort_ph[0].pt > 35.)))

        sel2_p = sel1_p.refine("idPhoton", cut = op.AND((op.rng_len(idPhotons) >= 2), (idPhotons[0].pt > 35.)))

        sel1_e = noSel.refine("OneE", cut = op.AND(op.rng_len(sort_el) >= 1))
        sel2_e = sel1_e.refine("idElectron", cut = op.AND(op.rng_len(idElectrons) >= 1))

        sel1_m = noSel.refine("OneM", cut = op.AND(op.rng_len(sort_mu) >= 1))
        sel2_m = sel1_m.refine("idMuon", cut = op.AND(op.rng_len(idMuons) >= 1))

        
        #plots
        
        #sel1_p
        plots.append(Plot.make1D("LeadingPhotonPTNoID", sort_ph[0].pt, sel1_p, EqB(30, 0., 300.), title="Leading Photon pT"))
        
        plots.append(Plot.make1D("SubLeadingPhotonPTNoID", sort_ph[1].pt, sel1_p, EqB(30, 0., 300.), title="SubLeading Photon pT"))
       
       #sel2_p 
        
        plots.append(Plot.make1D("LeadingPhotonPTID", idPhotons[0].pt, sel2_p, EqB(30, 0., 300.), title="Leading Photon pT"))
            
        plots.append(Plot.make1D("SubLeadingPhotonPTID", idPhotons[0].pt, sel2_p, EqB(30, 0., 300.), title="SubLeading Photon pT")) 
       
       #sel1_e
        plots.append(Plot.make1D("LeadingElectronNoID", sort_el[0].pt, sel1_e, EqB(30, 0., 300.), title="Leading Electron pT"))
       #sel2_e
        plots.append(Plot.make1D("LeadingElectronID", idElectrons[0].pt, sel2_e, EqB(30, 0., 300.), title="Leading Electron pT"))

       #sel1_m
        plots.append(Plot.make1D("LeadingMuonNoID", sort_mu[0].pt, sel1_m, EqB(30, 0., 300.), title="Leading Muon pT"))
       #sel2_m
        plots.append(Plot.make1D("LeadingMuonID", idMuons[0].pt, sel2_m, EqB(30, 0., 300.), title="Leading Muon pT"))

    
       ##sel4
       # plots.append(Plot.make1D("LeadingPhotonPtSel4", sorted_ph[0].pt, sel4, EqB(30, 0., 250.), title="Leading Photon pT"))
       #
       # plots.append(Plot.make1D("SubLeadingPhotonPtSel4", sorted_ph[1].pt, sel4, EqB(30, 0., 250.), title="SubLeading Photon pT"))    
       #
       ##sel5
       # plots.append(Plot.make1D("LeadingElectronPtNOID", sort_el[0].pt, noSel, EqB(30, 0., 250.), title="Leading Electron pT")) 
       # plots.append(Plot.make1D("LeadingElectronPtID", sorted_el[0].pt, noSel, EqB(30, 0., 250.), title="Leading Electron pT"))

   

       #diphoton invariant mass plot
        #plots.append(Plot.make1D("Inv_mass_ggSel1",mGG,sel1,EqB(50, 100.,150.), title = "m_{\gamma\gamma}")) #segmentation error? how?
        #plots.append(Plot.make1D("Inv_mass_ggSel2",mGG,sel2,EqB(50, 100.,150.), title = "m_{\gamma\gamma}"))
        #plots.append(Plot.make1D("Inv_mass_ggSel3",mGG,sel3,EqB(50, 100.,150.), title = "m_{\gamma\gamma}"))
        #plots.append(Plot.make1D("Inv_mass_ggSel4",mGG,sel4,EqB(50, 100.,150.), title = "m_{\gamma\gamma}"))
         
       #HH invariant mass  
       # plots.append(Plot.make1D("Inv_mass_HH",mHH,sel4,EqB(50, 200.,1000.), title = "m_{HH}"))


       #yields
        yields = CutFlowReport("yields", recursive=True, printInLog=True)
        plots.append(yields)
        yields.add(noSel, title= 'noSel')
        yields.add(sel1_p, title='sel1')
        yields.add(sel2_p, title='sel2')

        #yields.add(sel3, title='sel3')
        #yields.add(sel4, title='sel4')
        #yields.add(sel5, title='sel5')

        return plots


def postProcess(self, taskList, config=None, workdir=None, resultsdir=None):
    from bamboo.plots import CutFlowReport
    if not self.plotList:
        self.plotList = self.getPlotList(resultsdir=resultsdir, config=config)
    # pretend the list of plots doesn't have any CutFlowReport
    plotList_bk = self.plotList
    self.plotList = [ ap for ap in self.plotList if not isinstance(ap, CutFlowReport) ]
    super().postProcess(taskList, config=config, workdir=workdir, resultsdir=resultsdir)
    self.plotList = plotList_bk # restore
    # custom CutFlowReport printing 
## BEGIN cutflow reports, adapted from bamboo.analysisutils

import logging
logger = logging.getLogger(__name__)
import os.path
from bamboo.analysisutils import loadPlotIt

_yieldsTexPreface = "\n".join(f"{ln}" for ln in
r"""\documentclass[12pt, landscape]{article}
\usepackage[margin=0.5in]{geometry}
\begin{document}
""".split("\n"))

def _texProcName(procName):
    if ">" in procName:
        procName = procName.replace(">", "$ > $")
    if "=" in procName:
        procName = procName.replace("=", "$ = $")
    if "_" in procName:
        procName = procName.replace("_", "\_")
    return procName

def _makeYieldsTexTable(report, samples, entryPlots, stretch=1.5, orientation="v", align="c", yieldPrecision=1, ratioPrecision=2):
    if orientation not in ("v", "h"):
        raise RuntimeError(f"Unsupported table orientation: {orientation} (valid: 'h' and 'v')")
    import plotit.plotit
    from plotit.plotit import Stack
    import numpy as np
    from itertools import repeat, count
    def colEntriesFromCFREntryHists(report, entryHists, precision=1):
        stacks_t = [ (entryHists[entries[0]] if len(entries) == 1 else
            Stack(entries=[entryHists[eName] for eName in entries]))
            for entries in report.titles.values() ]
        return stacks_t, [ "& {0:.2e}".format(st_t.contents[1]) for st_t in stacks_t ]
    def colEntriesFromCFREntryHists_forEff(report, entryHists, precision=1):
        stacks_t = [ (entryHists[entries[0]] if len(entries) == 1 else
            Stack(entries=[entryHists[eName] for eName in entries]))
            for entries in report.titles.values() ]
        return stacks_t, [ " {0} ".format(st_t.contents[1]) for st_t in stacks_t ]
    smp_signal = [smp for smp in samples if smp.cfg.type == "SIGNAL"]
    smp_mc = [smp for smp in samples if smp.cfg.type == "MC"]
    smp_data = [smp for smp in samples if smp.cfg.type == "DATA"]
    sepStr_v = "|l|"
    hdrs = ["Selection"]
    entries_smp = [ [_texProcName(tName) for tName in report.titles.keys()] ]
    stTotMC, stTotData = None, None
    if smp_signal:
        sepStr_v += "|"
        for sigSmp in smp_signal:
            _, colEntries = colEntriesFromCFREntryHists(report,
                { eName : sigSmp.getHist(p) for eName, p in entryPlots.items() }, precision=yieldPrecision)
            sepStr_v += f"{align}|"
            hdrs.append(f"{_texProcName(sigSmp.cfg.yields_group)} {sigSmp.cfg.cross_section:f}pb")
            entries_smp.append(colEntries)
    if smp_mc:
        sepStr_v += "|"
        sel_list = []
        for mcSmp in smp_mc:
            _, colEntries = colEntriesFromCFREntryHists(report,
                { eName : mcSmp.getHist(p) for eName, p in entryPlots.items() }, precision=yieldPrecision)
            sepStr_v += f"{align}|"
            if isinstance(mcSmp, plotit.plotit.Group):
                hdrs.append(_texProcName(mcSmp.name))
            else:
                hdrs.append(_texProcName(mcSmp.cfg.yields_group))
            entries_smp.append(_texProcName(colEntries))
            _, colEntries_forEff = colEntriesFromCFREntryHists_forEff(report,
                { eName : mcSmp.getHist(p) for eName, p in entryPlots.items() }, precision=yieldPrecision)
            colEntries_matrix = np.array(colEntries_forEff)
            sel_eff = np.array([100])
            for i in range(1, len(report.titles)):
                sel_eff = np.append(sel_eff, [ float(colEntries_matrix[i]) / float(colEntries_matrix[i-1]) *100 ]).tolist()
            for i in range(len(report.titles)):
                sel_eff[i] = str(f"({sel_eff[i]:.2f}\%)")
            entries_smp.append(sel_eff)
            sel_list.append(colEntries_forEff)
        from bamboo.root import gbl
        sel_list_array = np.array(sel_list)
        gbl.gStyle.SetPalette(1)
        c1 = gbl.TCanvas("c1", "c1", 600, 400)
        cutflow_histo_FS = gbl.TH1F("cutflow_histo", "Selection Cutflow", 6, 0, 6)
        cutflow_histo_FS.GetXaxis().SetTitle("Selection")
        cutflow_histo_FS.GetYaxis().SetTitle("Nevent")
        cutflow_histo_Delphes = gbl.TH1F("cutflow_histo", "Delphes", 6, 0, 6)
        for i in range(len(colEntries_forEff)):
            cutflow_histo_FS.Fill(i, float(sel_list_array[0,i]))
        cutflow_histo_FS.SetLineColor(2)
        cutflow_histo_FS.SetLineWidth(3)
        for i in range(len(colEntries_forEff)):
            cutflow_histo_Delphes.Fill(i, float(sel_list_array[1,i]))
        cutflow_histo_Delphes.SetLineColor(4)
        cutflow_histo_Delphes.SetLineWidth(3)
        cutflow_histo_FS.Draw("HIST")
        cutflow_histo_Delphes.Draw("SAME HIST")
        gbl.gPad.SetLogy()
        leg = gbl.TLegend(0.78,0.695,0.980,0.935)
        leg.AddEntry(cutflow_histo_Delphes, "Delphes", "l")
        leg.AddEntry(cutflow_histo_FS, "FS", "l")
        leg.Draw()
        c1.SaveAs("cutflow.gif")
        logger.info("Plot for selection cutflow is available")
    if smp_data:
        sepStr_v += f"|{align}|"
        hdrs.append("Data")
        stTotData, colEntries = colEntriesFromCFREntryHists(report, { eName : Stack(entries=[smp.getHist(p) for smp in smp_data]) for eName, p in entryPlots.items() }, precision=yieldPrecision)
        entries_smp.append(colEntries)
    if smp_data and smp_mc:
        sepStr_v += f"|{align}|"
        hdrs.append("Data/MC")
        colEntries = []
        for stData,stMC in zip(stTotData, stTotMC):
            dtCont = stData.contents
            mcCont = stMC.contents
            ratio = np.where(mcCont != 0., dtCont/mcCont, np.zeros(dtCont.shape))
            ratioErr = np.where(mcCont != 0., np.sqrt(mcCont**2*stData.sumw2 + dtCont**2*(stMC.sumw2+stMC.syst2))/mcCont**2, np.zeros(dtCont.shape))
            colEntries.append("${{0:.{0}f}} \pm {{1:.{0}f}}$".format(ratioPrecision).format( ratio[1], ratioErr[1]))
        entries_smp.append(colEntries)
    if len(colEntries) < 2:
        logger.warning("No samples, so no yields.tex")
    return "\n".join(([
        f"\\begin{{tabular}}{{ {sepStr_v} }}",
        "    \\hline",
        "    {0} \\\\".format(" & ".join(hdrs)),
        "    \\hline"]+[
            "    {0} \\\\".format(" ".join(smpEntries[i] for smpEntries in entries_smp))
            for i in range(len(report.titles)) ] )+[
        "    \\hline",
        "\\end{tabular}",
        "\\end{document}"
        ])

def printCutFlowReports(config, reportList, workdir=".", resultsdir=".", readCounters=lambda f : -1., eras=("all", None), verbose=False):
    """
    Print yields to the log file, and write a LaTeX yields table for each

    Samples can be grouped (only for the LaTeX table) by specifying the
    ``yields-group`` key (overriding the regular ``groups`` used for plots).
    The sample (or group) name to use in this table should be specified
    through the ``yields-title`` sample key.

    In addition, the following options in the ``plotIt`` section of
    the YAML configuration file influence the layout of the LaTeX yields table:

    - ``yields-table-stretch``: ``\\arraystretch`` value, 1.15 by default
    - ``yields-table-align``: orientation, ``h`` (default), samples in rows, or ``v``, samples in columns
    - ``yields-table-text-align``: alignment of text in table cells (default: ``c``)
    - ``yields-table-numerical-precision-yields``: number of digits after the decimal point for yields (default: 1)
    - ``yields-table-numerical-precision-ratio``: number of digits after the decimal point for ratios (default: 2)
    """
    eraMode, eras = eras
    if not eras: ## from config if not specified
        eras = list(config["eras"].keys())
    ## helper: print one bamboo.plots.CutFlowReport.Entry
    def printEntry(entry, printFun=logger.info, recursive=True, genEvents=None):
        effMsg = ""
        if entry.parent:
            sumPass = entry.nominal.GetBinContent(1)
            sumTotal = entry.parent.nominal.GetBinContent(1)
            if sumTotal != 0.:
                effMsg = f", Eff={sumPass/sumTotal:.2%}"
                if genEvents:
                    effMsg += f", TotalEff={sumPass/genEvents:.2%}"
        printFun(f"Selection {entry.name}: N={entry.nominal.GetEntries()}, SumW={entry.nominal.GetBinContent(1)}{effMsg}")
        if recursive:
            for c in entry.children:
                printEntry(c, printFun=printFun, recursive=recursive, genEvents=genEvents)
    ## retrieve results files, get generated events for each sample
    from bamboo.root import gbl
    resultsFiles = dict()
    generated_events = dict()
    for smp, smpCfg in config["samples"].items():
        if "era" not in smpCfg or smpCfg["era"] in eras:
            resF = gbl.TFile.Open(os.path.join(resultsdir, f"{smp}.root"))
            resultsFiles[smp] = resF
            genEvts = None
            if "generated-events" in smpCfg:
                if isinstance(smpCfg["generated-events"], str):
                    genEvts = readCounters(resF)[smpCfg["generated-events"]]
                else:
                    genEvts = smpCfg["generated-events"]
            generated_events[smp] = genEvts
    has_plotit = None
    try:
        import plotit.plotit
        has_plotit = True
    except ImportError:
        has_plotit = False
    from bamboo.plots import EquidistantBinning as EqB
    class YieldPlot:
        def __init__(self, name):
            self.name = name
            self.plotopts = dict()
            self.axisTitles = ("Yield",)
            self.binnings = [EqB(1, 0.,1.)]
    for report in reportList:
        smpReports = { smp: report.readFromResults(resF) for smp, resF in resultsFiles.items() }
        ## debug print
        for smp, smpRep in smpReports.items():
            if smpRep.printInLog:
                logger.info(f"Cutflow report {report.name} for sample {smp}")
                for root in smpRep.rootEntries():
                    printEntry(root, genEvents=generated_events[smp])
        ## save yields.tex (if needed)
        if any(len(cb) > 1 or tt != cb[0] for tt,cb in report.titles.items()):
            if not has_plotit:
                logger.error(f"Could not load plotit python library, no TeX yields tables for {report.name}")
            else:
                yield_plots = [ YieldPlot(f"{report.name}_{eName}") for tEntries in report.titles.values() for eName in tEntries ]
                out_eras = []
                if len(eras) > 1 and eraMode in ("all", "combined"):
                    out_eras.append((f"{report.name}.tex", eras))
                if len(eras) == 1 or eraMode in ("split", "all"):
                    for era in eras:
                        out_eras.append((f"{report.name}_{era}.tex", [era]))
                for outName, iEras in out_eras:
                    pConfig, samples, plots, _, _ = loadPlotIt(config, yield_plots, eras=iEras, workdir=workdir, resultsdir=resultsdir, readCounters=readCounters)
                    tabBlock = _makeYieldsTexTable(report, samples,
                            { p.name[len(report.name)+1:]: p for p in plots },
                            stretch=pConfig.yields_table_stretch,
                            orientation=pConfig.yields_table_align,
                            align=pConfig.yields_table_text_align,
                            yieldPrecision=pConfig.yields_table_numerical_precision_yields,
                            ratioPrecision=pConfig.yields_table_numerical_precision_ratio)
                    with open(os.path.join(workdir, outName), "w") as ytf:
                        ytf.write("\n".join((_yieldsTexPreface, tabBlock)))
                    logger.info("Yields table for era(s) {0} was written to {1}".format(",".join(eras), os.path.join(workdir, outName)))

## END cutflow reports, adapted from bamboo.analysisutils
