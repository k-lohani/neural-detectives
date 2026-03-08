import React from 'react';
import '../index.css';

const LogicGrid = ({ caseData, gridState = {} }) => {
    if (!caseData) return null;

    const suspects = caseData.suspects?.map(s => s.name) || [];
    const weapons = caseData.weapons?.map(w => w.name) || [];
    const locations = caseData.locations?.map(l => l.name) || [];

    const getCell = (row, col) => {
        const key1 = `${row}|${col}`;
        const key2 = `${col}|${row}`;
        const val = gridState[key1] !== undefined ? gridState[key1] : gridState[key2];
        if (val === true) return { char: 'O', cls: 'truth-cell' };
        if (val === false) return { char: 'X', cls: 'false-cell' };
        return { char: '', cls: '' };
    };

    const renderSubgrid = (rowItems, colItems) => (
        <div className="subgrid" style={{ gridTemplateColumns: `repeat(${colItems.length}, 1fr)` }}>
            {rowItems.map(r =>
                colItems.map(c => {
                    const { char, cls } = getCell(r, c);
                    return (
                        <div key={`${r}-${c}`} className={`grid-cell ${cls}`}>
                            {char}
                        </div>
                    );
                })
            )}
        </div>
    );

    return (
        <div className="logic-grid-container">
            <div className="grid-header">
                <h3>Detective's Logic Grid</h3>
                <span className="grid-hint">Determined automatically by conversation</span>
            </div>

            <div className="murdle-grid">
                {/* ── Column headers ── */}
                <div className="murdle-corner" />
                <div className="murdle-col-group">
                    <div className="col-group-label">Suspects</div>
                    <div className="col-labels">
                        {suspects.map(s => (
                            <div key={s} className="col-label" title={s}><span>{s}</span></div>
                        ))}
                    </div>
                </div>
                <div className="murdle-col-group">
                    <div className="col-group-label">Locations</div>
                    <div className="col-labels">
                        {locations.map(l => (
                            <div key={l} className="col-label" title={l}><span>{l}</span></div>
                        ))}
                    </div>
                </div>

                {/* ── Row 1: Weapons ── */}
                <div className="murdle-row-labels">
                    {weapons.map(w => (
                        <div key={w} className="row-label" title={w}>{w}</div>
                    ))}
                </div>
                {renderSubgrid(weapons, suspects)}
                {renderSubgrid(weapons, locations)}

                {/* ── Row 2: Locations ── */}
                <div className="murdle-row-labels">
                    {locations.map(l => (
                        <div key={l} className="row-label" title={l}>{l}</div>
                    ))}
                </div>
                {renderSubgrid(locations, suspects)}
                <div className="subgrid-empty" />
            </div>
        </div>
    );
};

export default LogicGrid;
