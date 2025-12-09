/*
 * Copyright (c) Ioannis E. Kommas 2025. All Rights Reserved
 */

UPDATE ESFIEinvoiceProviderDetails
SET
    Status='2',
    Statuscode='9',
    IssueDate=ESDCreated
WHERE
    fDocumentGID=:unique_id